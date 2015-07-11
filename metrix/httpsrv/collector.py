from functools import wraps

from flask import Flask, request

from metrix import config
from metrix.logic.collector import Collector
from metrix.httpsrv.base import json_request

app = Flask(__name__)
collector = Collector()

@app.route('/ping', methods=['GET'])
def ping():
    return 'pong'

@app.route('/events', methods=['POST'])
@json_request
def events(payload):
    events = payload.get('events')
    return collector.enque(events)

@app.route('/shutdown', methods=['POST'])
@json_request
def handle_shutdown(payload):
    shutdown_func = request.environ.get('werkzeug.server.shutdown')
    if shutdown_func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    shutdown_func()
    return {'rc': 0}

def start_server(config_file):
    config.init(config_file)
    cfg = config.get_instance()
    collector.init(cfg)
    app.run(cfg.bind, cfg.port)
