from .provider import load_backends
from .model import Environment, Equipment

# built-in plugin loading
pytest_plugins = (
    'lab.storage',
    'lab.roles',
    'lab.runnerctl',
    'lab.logwatch',
    'lab.log',
    'lab.warnreporter',
    'lab.network.plugin',
)
