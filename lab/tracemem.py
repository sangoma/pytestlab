"""
Trace local memory allocations per test.
"""
import linecache
import os
from collections import deque
import logging
import pytest

try:
    import tracemalloc
except ImportError:
    logging.warn("No no tracemalloc support")


log = logging.getLogger("pytestlab.memtrace")


def top_lines(snapshot, key_type='lineno', limit=10):
    """Taken the stdlib's `pretty top`_ example.

    .. _pretty top:
        https://docs.python.org/3/library/tracemalloc.html#pretty-top
    """
    snapshot = snapshot.filter_traces((
        tracemalloc.Filter(False, "<frozen importlib._bootstrap>"),
        tracemalloc.Filter(False, "<unknown>"),
    ))
    top_stats = snapshot.statistics(key_type)

    lines = []
    lines.append("Top %s lines" % limit)
    for index, stat in enumerate(top_stats[:limit], 1):
        frame = stat.traceback[0]
        # replace "/path/to/module/file.py" with "module/file.py"
        filename = os.sep.join(frame.filename.split(os.sep)[-2:])
        lines.append("#%s: %s:%s: %.1f KiB" % (
            index, filename, frame.lineno, stat.size / 1024))
        line = linecache.getline(frame.filename, frame.lineno).strip()
        if line:
            lines.append('    %s' % line)

        other = top_stats[limit:]
        if other:
            size = sum(stat.size for stat in other)
        lines.append("%s other: %.1f KiB" % (len(other), size / 1024))
        total = sum(stat.size for stat in top_stats)
        lines.append("Total allocated size: %.1f KiB" % (total / 1024))

    return lines


class MemTracer(object):
    """Local memory tracing with snapshots collected between each test.
    Useful for debugging local memory leaks in downstream tools or test code.
    """
    def __init__(self, config):
        self.config = config
        tracemalloc.start()
        self.snapshots = {}
        self.snap_deque = deque(max=10)

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_setup(self, item):
        """Collect memory traces before and after fixture setup.
        """
        pytest.set_trace()
        presetup = tracemalloc.take_snapshot()
        self.snap_deque.append(presetup)
        self.snapshots["pre-setup_{}".format(item.node.name)] = presetup
        yield
        pytest.set_trace()
        postsetup = tracemalloc.take_snapshot()
        self.snap_deque.append(postsetup)
        self.snapshots["post-setup_{}".format(item.node.name)] = postsetup

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_teardown(self, item, nextitem):
        """Collect memory traces before and after fixture teardown.
        """
        presetup = self.snap_deque[-1]
        preteardown = tracemalloc.take_snapshot()
        self.snap_deque.append(preteardown)
        self.snapshots["pre-teardown_{}".format(item.node.name)] = preteardown
        yield
        postteardown = tracemalloc.take_snapshot()
        self.snap_deque.append(postteardown)
        self.snapshots["post-teardown_{}".format(item.node.name)] = postteardown


@pytest.hookimpl
def pytest_configure(config):
    """Register the mem tracer and start tracing.
    """
    memtracer = MemTracer(config)
    pytest.memtracer = memtracer
    memtracer.start()
    config.pluginmanager.register(memtracer, name='MemTracer')
