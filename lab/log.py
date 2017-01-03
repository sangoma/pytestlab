from builtins import str
import pytest
import sys
import colorlog
import logging
import logging.config


DATEFMT = '%b %d %H:%M:%S'
FORMAT = "%(asctime)s [%(levelname)s] %(name)s %(filename)s:"\
    "%(lineno)d : %(message)s"


def pytest_namespace():
    return {'log': logging.getLogger('pytestlab')}


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    storage = config.pluginmanager.getplugin("storage")
    assert storage, "No storage found"

    level = config.getoption('--loglevel')
    isatty = sys.stdout.isatty()
    logging.config.dictConfig({
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {
            'stream': {
                'class': 'logging.StreamHandler',
                'formatter': 'colored' if isatty else 'default'
            },
            'file': {
                'class': 'logging.FileHandler',
                'formatter': 'default',
                'filename': str(storage.root.join('pytest.log'))
            }
        },
        'formatters': {
            'default': {
                'format': FORMAT,
                'datefmt': DATEFMT
            },
            'colored': {
                '()': colorlog.ColoredFormatter,
                'format': "%(log_color)s" + FORMAT,
                'datefmt': DATEFMT,
                'log_colors': {
                    'CRITICAL': 'bold_red',
                    'ERROR': 'red',
                    'WARNING': 'purple',
                    'INFO': 'green',
                    'DEBUG': 'yellow'
                }
            }
        },
        'loggers': {
            '': {
                'handlers': ['stream', 'file'],
                'level': getattr(logging, level.upper()),
                'propagate': True
            },
            'sangoma.configurators': {
                'level': 'INFO',
            },
            'tftpy': {
                'level': 'WARNING',
            },
        }
    })


def pytest_addoption(parser):
    group = parser.getgroup('logging')
    group.addoption('--loglevel', action='store', default='info',
                    choices=['critical', 'warning', 'info', 'debug'],
                    help="jenkins job name corresponding to the current "
                         "caller of this pytest session/invocation")


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    storage = item.config.pluginmanager.getplugin("storage")
    if storage:
        store = storage.get_storage(item)

        formatter = logging.Formatter(FORMAT, datefmt=DATEFMT)
        handler = logging.FileHandler(str(store.join('pytest.log')))
        handler.setFormatter(formatter)
        logging.root.addHandler(handler)
        item.config.loghandler = handler

    pytest.log.info("Starting {}...".format(item.name))


def pytest_runtest_teardown(item):
    try:
        logging.root.removeHandler(item.config.loghandler)
    except AttributeError:
        pass


@pytest.fixture
def log(request):
    'return a logging.logger instance for this test session'
    return pytest.log.getChild(request.node.name.partition('[')[0])
