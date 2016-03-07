import setuptools
from setuptools.command.test import test as TestCommand


class PyTest(TestCommand):
    user_options = [('pytest-args=', 'a', "Arguments to pass to py.test")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = []

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # import here, cause outside the eggs aren't loaded
        import sys
        import shlex
        import pytest

        errno = pytest.main(['tests/'] + shlex.split(self.pytest_args or ''))
        sys.exit(errno)


setup_params = dict(
    name='lab',
    version='0.0.0',
    packages=setuptools.find_packages(),
    install_requires=[
        # TODO: figure out what belongs here and what belongs inside
        # the requirements file.
        'beautifulsoup4',
        'bs4',
        'click',
        'colorlog',
        'contextlib2',
        'dnspython',
        'enum34',
        'ipaddress',
        'jenkinsapi',
        'libarchive',
        'lxml',
        'paramiko',
        'plumbum',
        'psycopg2',
        'pymongo',
        'pymysql',
        'pyroute2',
        'pytest',
        'pytest-instafail',
        'pytest-ordering',
        'python-etcd',
        'python-redmine',
        'pyxdg',
        'rpyc',
        'six',
        'SQLAlchemy',
        'srvlookup',
        'subprocess32'
    ],
    extras_require={
        'build': ['pycparser', 'cffi'],
    },
    tests_require=['pytest'],
    cmdclass={'test': PyTest},
    entry_points={'console_scripts': ['labctl=lab.client:cli',
                                      'labagent=lab.agent:cli']},
    cffi_modules=["sangoma/trace/pcap_build.py:ffi"]
)

if __name__ == '__main__':
    setuptools.setup(**setup_params)
