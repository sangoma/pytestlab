#
# Copyright 2017 Sangoma Technologies Inc.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
Log monitoring and capture.
"""
from __future__ import division
from builtins import next
from builtins import object
import pytest
from collections import defaultdict
from lab.logwatch import logfiles, journal


class LogManager(object):
    """Remote log management and capture on a per test basis.
    """
    def __init__(self, config):
        self.config = config
        self.sources = defaultdict(list)
        self.recovered_logs = {}

    def register(self, source):
        """Register a role ctl with a log file table to be watched.
        """
        source.prepare()
        self.sources[source.ctl].append(source)

    def _capture_logs(self, ctl, sources):
        ctl_logs = self.recovered_logs.setdefault(ctl, {})
        for source in sources:
            ctl_logs.update(source.capture())

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_setup(self, item):
        """Truncate all logs prior to fixture invocations.
        """
        self.recovered_logs = {}
        self.config.hook.pytest_lab_log_rotate()
        for sources in self.sources.values():
            for source in sources:
                source.prepare()
        yield

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_teardown(self, item, nextitem):
        """Collect and store logs on test teardown.
        """
        yield
        for ctl, sources in self.sources.items():
            self._capture_logs(ctl, sources)

        self.config.hook.pytest_lab_process_logs(
            config=self.config, item=item, logs=self.recovered_logs)

    @pytest.hookimpl(trylast=True)
    def pytest_lab_role_destroyed(self, config, ctl):
        sources = self.sources.pop(ctl, None)
        if sources:
            self._capture_logs(ctl, sources)


@pytest.hookimpl(trylast=True)
def pytest_configure(config):
    """Register the log watch manager.
    """
    logmanager = LogManager(config)
    pytest.logmanager = logmanager
    # allow plugins to register for log watching
    config.hook.pytest_lab_log_watch.call_historic(
        kwargs=dict(logmanager=logmanager))
    config.pluginmanager.register(logmanager, name='LogManager')


def pytest_addhooks(pluginmanager):
    """Add log watch plugin hooks spec.
    """
    class LogHooks:
        @pytest.hookspec
        def pytest_lab_process_logs(config, item, logs):
            """Broadcast all collected log files and where it came from
            to all subscribers.
            """

        @pytest.hookspec(historic=True)
        def pytest_lab_log_watch(logmanager):
            """Register a role ctl and a log file table to be watched and
            processed.
            """

        @pytest.hookspec
        def pytest_lab_log_rotate(config):
            """Called to indicate to role plugins to rotate their logs."""

    pluginmanager.add_hookspecs(LogHooks())
