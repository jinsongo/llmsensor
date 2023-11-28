import asyncio, uuid, os, warnings
import traceback
from contextvars import ContextVar
from datetime import datetime, timezone
from collections import defaultdict

from .parsers import (
    default_input_parser,
    default_output_parser,
)
from .openai_utils import OpenAIUtils
from .event_queue import EventQueue
from .consumer import Consumer
from .users import user_ctx, user_props_ctx, identify
from .tags import tags_ctx, tags

run_ctx = ContextVar("run_ids", default=None)

queue = EventQueue()
consumer = Consumer(queue)

consumer.start()

def nested_dictionary():
    return defaultdict(DictionaryOfStan)

# Simple implementation of a nested dictionary.
DictionaryOfStan = nested_dictionary


def track_event(
    event_type,
    event_name,
    run_id,
    parent_run_id=None,
    name=None,
    input=None,
    output=None,
    error=None,
    token_usage=None,
    user_id=None,
    user_props=None,
    tags=None,
    extra=None,
    metadata=None,
):
    # Load here in case load_dotenv done after
    AGENT_KEY = "llm-openai-key"
    VERBOSE = os.environ.get("LOG_VERBOSE")

    event = {
        "event": event_name if event_name else "None",
        "type": event_type if event_type else "None",
        "app": AGENT_KEY,
        "name": name if name else "None",
        "userId": user_id if user_id else "None",
        "userProps": user_props if user_props else "None",
        "tags": "None",
        "runId": str(run_id),
        "parentRunId": str(parent_run_id) if parent_run_id else "None",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "input": input if input else "None",
        "output": output if output else "None",
        "error": error if error else "None",
#       "extra": extra,
        "runtime": "llmsensor",
        "tokens": token_usage,
        "metadata": metadata if metadata else "None",
    }

    plugin_data = dict()
    try:
        plugin_data["name"] = "com.instana.plugin.openai"
        plugin_data["entityId"] = "Openai"
        plugin_data["event"] = event_name,
        plugin_data["type"] = event_type,
        plugin_data["app"] = AGENT_KEY
        plugin_data["name"] = name if name else "None",
        plugin_data["userId"] = user_id if user_id else "None",
        plugin_data["userProps"] = "None",
        plugin_data["tags"] = "None"
        plugin_data["runId"] = str(run_id)
        plugin_data["timestamp"] = datetime.now(timezone.utc).isoformat()
        plugin_data["input"] = input[0]["text"] if input and input != "None" else "None"
        plugin_data["output"] = output["text"] if output else "None"
        plugin_data["error"] = "None"
        plugin_data["runtime"] = "openai"
        plugin_data["metadata"] = "None"
        plugin_data["metrics"] = DictionaryOfStan()
        plugin_data["metrics"]["tokens"] = token_usage["completion"] if token_usage else 0

    except Exception as e:
        print("_collect_metrics:", e)

    if VERBOSE:
        print("llmsensor_add_event", event)

    queue.append(plugin_data)


def handle_internal_error(e):
    print("[llmsensor] Error: ", e)


def wrap(
    fn,
    type=None,
    name=None,
    user_id=None,
    user_props=None,
    tags=None,
    input_parser=default_input_parser,
    output_parser=default_output_parser,
):
    def sync_wrapper(*args, **kwargs):
        output = None
        try:
            parent_run_id = run_ctx.get()
            run_id = uuid.uuid4()
            token = run_ctx.set(run_id)
            parsed_input = input_parser(*args, **kwargs)
            print("DEBUG: parsed_input:")
            print(parsed_input)

            track_event(
                type,
                "start",
                run_id,
                parent_run_id,
                input=parsed_input["input"],
                name=name or parsed_input["name"],
                user_id=kwargs.pop("user_id", None) or user_ctx.get() or user_id,
                user_props=kwargs.pop("user_props", None)
                or user_props
                or user_props_ctx.get(),
                tags=kwargs.pop("tags", None) or tags or tags_ctx.get(),
#               extra=parsed_input["extra"],
            )
        except Exception as e:
            handle_internal_error(e)

        try:
            output = fn(*args, **kwargs)
        except Exception as e:
            track_event(
                type,
                "error",
                run_id,
                error={"message": str(e), "stack": traceback.format_exc()},
            )

            # rethrow error
            raise e

        try:
            parsed_output = output_parser(output)
            print("DEBUG: parsed_output:")
            print(parsed_output)

            track_event(
                type,
                "end",
                run_id,
                # Need name in case need to compute tokens usage server side,
                name=name or parsed_input["name"],
                output=parsed_output["output"],
                token_usage=parsed_output["tokens"],
            )
            return output
        except Exception as e:
            handle_internal_error(e)

        run_ctx.reset(token)
        return output

    async def async_wrapper(*args, **kwargs):
        output = None
        try:
            parent_run_id = run_ctx.get()
            run_id = uuid.uuid4()
            token = run_ctx.set(run_id)
            parsed_input = input_parser(*args, **kwargs)
            tags = kwargs.pop("tags", None)
            print("DEBUG: parsed_input:")
            print(parsed_input)

            track_event(
                type,
                "start",
                run_id,
                parent_run_id,
                input=parsed_input["input"],
                name=name or parsed_input["name"],
                user_id=user_ctx.get() or user_id or kwargs.pop("user_id", None),
                user_props=user_props_ctx.get()
                or user_props
                or kwargs.pop("user_props", None),
                tags=tags,
#               extra=parsed_input["extra"],
            )
        except Exception as e:
            handle_internal_error(e)

        try:
            output = await fn(*args, **kwargs)
        except Exception as e:
            track_event(
                type,
                "error",
                run_id,
                error={"message": str(e), "stack": traceback.format_exc()},
            )

            # rethrow error
            raise e

        try:
            parsed_output = output_parser(output)
            print("DEBUG: parsed_output:")
            print(parsed_output)

            track_event(
                type,
                "end",
                run_id,
                # Need name in case need to compute tokens usage server side,
                name=name or parsed_input["name"],
                output=parsed_output["output"],
                token_usage=parsed_output["tokens"],
            )
            return output
        except Exception as e:
            handle_internal_error(e)

        run_ctx.reset(token)
        return output

    return async_wrapper if asyncio.iscoroutinefunction(fn) else sync_wrapper


def monitor(object: OpenAIUtils):
    if object.__name__ == "openai":
        object.ChatCompletion.create = wrap(
            object.ChatCompletion.create,
            "llm",
            input_parser=OpenAIUtils.parse_input,
            output_parser=OpenAIUtils.parse_output,
        )

        object.ChatCompletion.acreate = wrap(
            object.ChatCompletion.acreate,
            "llm",
            input_parser=OpenAIUtils.parse_input,
            output_parser=OpenAIUtils.parse_output,
        )

    else:
        warnings.warn("You cannot monitor this object")


def agent(name=None, user_id=None, user_props=None, tags=None):
    def decorator(fn):
        return wrap(
            fn,
            "agent",
            name=name or fn.__name__,
            user_id=user_id,
            user_props=user_props,
            tags=tags,
            input_parser=default_input_parser,
        )

    return decorator


def tool(name=None, user_id=None, user_props=None, tags=None):
    def decorator(fn):
        return wrap(
            fn,
            "tool",
            name=name or fn.__name__,
            user_id=user_id,
            user_props=user_props,
            tags=tags,
            input_parser=default_input_parser,
        )

    return decorator
