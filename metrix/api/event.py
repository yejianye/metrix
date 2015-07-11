import json

import requests

_srv_info = {}
def _call(command, payload):
    resp = requests.post('http://{host}:{port}/{command}'.format(
        host=_srv_info['host'],
        port=_srv_info['port'],
        command=command),
        data = json.dumps(payload)
    )
    print resp.content
    return resp.json()

def init(host, port):
    """Initialize metrix collector client

    Args:
        host: hostname or IP of collector server
        port: port of collector server
    """
    _srv_info.update({
        'host': host,
        'port': port
    })

def send(event_or_list):
    """Send a single event or a list of events
    >>> send({
            'event_name':  'user created',
            'user_id': 123,
            'gender': 'Male',
            'platform': 'iOS'
        })

    Args:
        event_or_list: A single event (which would be a dict), or a list of events
    """
    if not isinstance(event_or_list, list):
        events = [event_or_list]
    else:
        events = event_or_list
    return _call('events', {'events': events})

def shutdown():
    """
    Shutdown collector server
    """
    return _call('shutdown', {})
