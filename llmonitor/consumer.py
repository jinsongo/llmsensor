import time, atexit, requests, os, json
from collections import defaultdict
from threading import Thread

DEFAULT_AGENT_URL = "https://127.0.0.1:42699"

def nested_dictionary():
    return defaultdict(DictionaryOfStan)

# Simple implementation of a nested dictionary.
DictionaryOfStan = nested_dictionary

class Discovery(object):
    pid = 0
    name = None
    args = None
    fd = -1
    inode = ""

    def __init__(self, **kwds):
        self.__dict__.update(kwds)

    def to_dict(self):
        kvs = dict()
        kvs['pid'] = self.pid
        kvs['name'] = self.name
        kvs['args'] = self.args
        kvs['fd'] = self.fd
        kvs['inode'] = self.inode
        return kvs

class Consumer(Thread):
   
    def __init__(self, event_queue):
        self.running = True
        self.event_queue = event_queue
        self.api_url = os.environ.get("AGENT_ENDPOINT_URL") or DEFAULT_AGENT_URL
        self.verbose = os.environ.get("LOG_VERBOSE") or False

        Thread.__init__(self, daemon=True)
        atexit.register(self.stop)

    def run(self):
        while self.running:
            self.announce_sensor()
            self.send_batch()
            time.sleep(3)

        self.send_batch()

    def send_batch(self):
        batch = self.event_queue.get_batch()
        
        if len(batch) > 0:

            if (self.verbose):
                 print("llmsensor: sending events", len(batch))

            try:
                if (self.verbose):
                    print("llmsensor: sending events to ", self.api_url)
               
                print("DEBUG: requests.post:")
                print(batch)

                # Report metrics
                instana_data_url = "http://127.0.0.1:42699/com.instana.plugin.openai.123456"
                response = requests.post(instana_data_url,
                    data=to_json(batch),
                    headers={"Content-Type": "application/json"},
                    timeout=0.8)

                print("llmsensor: events data:", to_json(batch))
                print("llmsensor: events sent.", response.status_code)

                if response.status_code != 200:
                    print("Error sending events")
            except Exception as e:

                print("Error sending events", e)

                self.event_queue.append(batch)

    def stop(self):
        print("DEBUG: to stop collection")
        self.running = False
        self.join()


    def announce_sensor(self):
        d = Discovery(pid="123456",
                    name="com.instana.plugin.openai", args=[])
        payload = self.announce(d)
        return payload


    def announce(self, discovery):
        """
        With the passed in Discovery class, attempt to announce to the host agent.
        """
        try:
            url = "http://127.0.0.1:42699/com.instana.plugin.openai.discovery"
            response = requests.put(url,
                                    data=to_json(discovery),
                                    headers={"Content-Type": "application/json"},
                                    timeout=0.8)
            print("announce: discovery data: ", to_json(discovery))
        except Exception as exc:
            print("announce: connection error (%s)", type(exc))
            return None
        if 200 <= response.status_code <= 204:
            None  # self.last_seen = datetime.now()
        if response.status_code != 200:
            print("announce: response status code (%s) is NOT 200", response.status_code)
            return None
        if isinstance(response.content, bytes):
            raw_json = response.content.decode("UTF-8")
        else:
            raw_json = response.content
        try:
            payload = json.loads(raw_json)
        except json.JSONDecodeError as e:
            print("announce: response is not JSON: (%s)", raw_json)
            return None
        if not hasattr(payload, 'get'):
            print("announce: response payload has no fields: (%s)", payload)
            return None
        if not payload.get('pid'):
            print("announce: response payload has no pid: (%s)", payload)
            return None
        if not payload.get('agentUuid'):
            print("announce: response payload has no agentUuid: (%s)", payload)
            return None
        return payload



def to_json(obj):
    """
    Convert obj to json.  Used mostly to convert the classes in json_span.py until we switch to nested
    dicts (or something better)

    :param obj: the object to serialize to json
    :return:  json string
    """
    try:
        def extractor(o):
            if not hasattr(o, '__dict__'):
                print("Couldn't serialize non dict type: %s", type(o))
                return {}
            else:
                return {k.lower(): v for k, v in o.__dict__.items() if v is not None}

        return json.dumps(obj, default=extractor, sort_keys=False, separators=(',', ':')).encode()
    except Exception:
        print("to_json non-fatal encoding issue: ", exc_info=True)
