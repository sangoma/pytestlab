#
# Copyright 2017 Sangoma Technologies Inc.
#
from .provider import get_providers
from .model import Environment, Facts

# built-in plugin loading
pytest_plugins = (
    'lab.roles',
    'lab.runnerctl',
    'lab.logwatch',
    'lab.log',
    'lab.warnreporter',
    'lab.network.plugin',
    'lab.ctl.rpc',
)
