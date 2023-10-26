import time, atexit, requests, os
from threading import Thread

DEFAULT_AGENT_URL = "https://127.0.0.1:42699"


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
            self.send_batch()
            time.sleep(5)

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
                response = requests.post(
                    self.api_url + "/com.instana.plugin.python.%d",
                    json={"events": batch},
                    headers={"Content-Type": "application/json"},
                    timeout=5
                )

                if (self.verbose):
                    print("llmsensor: events sent.", response.status_code)

                if response.status_code != 200:
                    print("Error sending events")
            except Exception as e:

                if (self.verbose):
                    print("Error sending events", e)

                self.event_queue.append(batch)

    def stop(self):
        self.running = False
        self.join()
