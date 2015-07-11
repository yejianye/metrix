import requests

class CollectorClient(object):
    def __init__(host='localhost', port=10811):
        self.server_url = 'http://{host}:{port}'.format(host=host,port=port)

    def send_event(self, event_name, properties):
        payload = {'name': event_name, 'properties': properties}
        requests.post(self.server_url + '/events', data=payload)
