def default_input_parser(*args, **kwargs):
    def serialize(args, kwargs):
        if not args and not kwargs:
            return None

        if len(args) == 1 and not kwargs:
            return args[0]

        input = list(args)
        if kwargs:
            input.append(kwargs)

        return input

    return {"input": serialize(args, kwargs)}


def default_output_parser(output):
    return {"output": output, "tokens": None}
