#
# Copyright 2017 Sangoma Technologies Inc.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from builtins import str
from builtins import object
import pytest
import collections
import warnings


def folded_warnings(warnings):
    messages = ((str(warning.filename),
                 str(warning.lineno),
                 str(warning.message)) for warning in warnings)

    for event, count in collections.Counter(messages).items():
        yield count, event


class WarningsManager(object):
    def __init__(self):
        warnings.simplefilter('always', DeprecationWarning)
        self.warnings = []

    @pytest.mark.hookwrapper
    def pytest_runtest_protocol(self, item, nextitem):
        with warnings.catch_warnings(record=True) as warning_list:
            yield
            self.warnings.extend(warning_list)

    def pytest_terminal_summary(self, terminalreporter):
        if not self.warnings:
            return

        tr = terminalreporter
        tr._tw.sep("=", "warnings summary info")
        for count, warning in folded_warnings(self.warnings):
            tr._tw.line('WARN [{}] {}:{}: {}'.format(count, *warning))


def pytest_configure(config):
    plugin = WarningsManager()
    config.pluginmanager.register(plugin, "warnings")
