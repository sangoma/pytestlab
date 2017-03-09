import pytest
import requests


class TestMarker(object):
    def __init__(self, config, url):
        self.url = url
        self.session = requests.session()

    def get_marks(self, env, testname):
        api_url = '{}/v1/{}/mark/{}'.format(self.url, env, testname)
        response = self.session.get(api_url)
        return response.json()

    @pytest.hookimpl(hookwrapper=True)
    def pytest_collection_modifyitems(self, session, config, items):
        env = config.getoption('--env')

        # TODO: Really naive, we need add a batch call. Until then,
        # this is going to be unworkable for anyone outside the
        # Toronto office...
        for item in items:
            for mark in self.get_marks(env, item.name):
                name = mark['name']
                args = mark.get('args', [])
                kwargs = mark.get('kwargs', {})

                pytest.log.info(
                    "Applying {} mark to {}".format(name, item.name)
                )

                mark = getattr(pytest.mark, name)(*args, **kwargs)
                item.add_marker(mark)

        # Proceed with the collection
        yield


def pytest_addoption(parser):
    parser.addoption('--api-service', action='store',
                     help='URL to centralized API service for dynamic marking')


@pytest.hookimpl(trylast=True)
def pytest_configure(config):
    """Register the log watch manager.
    """
    server = config.getoption('--api-service')
    if server:
        testmarker = TestMarker(config, server)
        config.pluginmanager.register(testmarker, name='TestMarker')
