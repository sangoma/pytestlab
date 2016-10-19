from .app.__main__ import load_backends
from .model import Environment, Equipment

# built-in plugin loading
pytest_plugins = ('lab.storage')
