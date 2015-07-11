import yaml

_cfg = None

def init(config_file):
    global _cfg
    _cfg = Config(config_file)

def get_instance():
    assert _cfg, "config object hasn't been initialized."
    return _cfg
    
class Config(object):
    def __init__(self, config_file):
        with open(config_file) as f:
            self._data = yaml.load(f)

    def __getattr__(self, attr):
        if attr in self._data:
            return self._data[attr]
        else:
            raise AttributeError(attr)
