import gevent
import gevent.monkey; gevent.monkey.patch_all()
import requests

from metrix.api import event as event_api
from metrix import httpsrv


server_port = 11811

collector_config = 'tests/collector_config.yml'

def setup():
    gevent.spawn(start_collector_server)
    # Hack, waiting for collector server to start
    gevent.sleep(0.1)
    event_api.init(host='localhost', port=server_port)

def start_collector_server():
    httpsrv.start_collector(collector_config)

def test_send_event():
    # Valid event
    event = {
        'event_name':  'user_created',
        'properties': {
            'user_id': 123,
            'gender': 'Male',
            'platform': 'iOS'
        }
    }
    ret = event_api.send(event)
    assert len(ret['invalid_events']) == 0
    gevent.sleep(2.0)

def test_invalid_event():
    # Event with invalid event name
    events = [
        # invalid event name
        {
            'event_name':  'invalid event name',
        },
        # invalid event property `gender`
        {
            'event_name':  'user_created',
            'properties': {
                'user_id': 123,
                'gender': 'Animal',
                'platform': 'iOS'
            }
        }
    ]
    ret = event_api.send(events)
    assert len(ret['invalid_events']) == 2

def teardown():
    event_api.shutdown()
