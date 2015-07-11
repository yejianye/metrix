import traceback
import json
from functools import wraps

from flask import request, jsonify, make_response

def json_request(func):
    @wraps(func)
    def wrapped():
        payload = json.loads(request.data)
        try:
            return jsonify(func(payload))
        except Exception as e:
            traceback.print_exc()
            return make_response((str(e), 500))
    return wrapped
