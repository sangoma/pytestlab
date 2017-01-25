import sys
import pytest


@pytest.hookimpl(hookwrapper=True)
def pytest_load_initial_conftests(early_config, parser, args):
    # Monkey patch imports for python2 before any conftests are loaded
    if sys.version_info[0] < 3:
        from future import standard_library
        standard_library.install_aliases()

    yield
