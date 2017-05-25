#
# Copyright 2017 Sangoma Technologies Inc.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from builtins import str
from builtins import next
from builtins import object
import pytest
import re
import plumbum
import py
import itertools
from lab.utils import encode_path


def sanitized_name(name):
    return re.sub('[^\[\]\.\w\s\d_-]', '_', name).strip()


class ArtifactPath(object):
    def __init__(self, path=None):
        if path is None:
            # autogenerate a tmpdir of the form '/tmp/pytest-<int>'
            self.path = plumbum.local.path(str(
                py.path.local.make_numbered_dir(
                    prefix="pytest-",
                    rootdir=py.path.local("/tmp/"),
                    keep=5,
                )
            ))
        else:
            self.path = plumbum.local.path(path)

        self.path.mkdir()
        for entity in self.path.list():
            self.path.join(entity).delete()

    def copy(self, remote, local=None):
        if not isinstance(remote, plumbum.Path):
            remote = plumbum.local.path(remote)
        target = self.path.join(local or remote.name)
        plumbum.path.copy(remote, target)
        return target

    def open(self, path, mode='r'):
        target = self.path.join(path)
        return target.open(mode)

    def substorage(self, path):
        target = self.path.join(path)
        return ArtifactPath(target)

    # plumbum compatability API
    def join(self, path):
        return self.path.join(path)

    def __str__(self):
        return str(self.path)

    @property
    def name(self):
        return self.path.name


class StorageManager(object):
    def __init__(self, root):
        self.root = ArtifactPath(root)
        self.storage_cache = {}
        self.counter = itertools.count(1)

    def join(self, path):
        try:
            return self.storage_cache[path]
        except KeyError:
            store = self.root.substorage(path)
            self.storage_cache[path] = store
            return store

    def get_storage(self, item):
        storagedir = getattr(item, '_storagedir', None)
        if not storagedir:
            storagedir = '{:03}-{}'.format(next(self.counter),
                                           sanitized_name(item.name))
            item._storagedir = storagedir
        return self.join(storagedir)

    def pytest_runtest_setup(self, item):
        # Make sure the test storage directory is created, even if the
        # test doesn't happen to use it
        self.get_storage(item)

    @pytest.hookimpl
    def pytest_lab_process_logs(self, config, item, logs):
        for ctl, logset in logs.items():
            prefix_path = '@'.join((ctl.name, ctl.hostname))
            prefix_dir = self.get_storage(item).join('logs').join(prefix_path)
            prefix_dir.mkdir()

            for remotefile, contents in logset.items():
                absname = filename = str(remotefile)

                # any plumbum remote path should be encoded as an
                # appropriate file name
                if getattr(remotefile, 'dirname', None):
                    absname = encode_path(absname)

                localfile = prefix_dir.join(absname)
                localfile.write(contents)
                pytest.log.info('Archived {}'.format(filename))


def pytest_addoption(parser):
    group = parser.getgroup('storage')
    group.addoption('--storage-root', action='store', dest='storage',
                    default=None, metavar='DIRECTORY',
                    help='set the target directory where test storage '
                         'should be stored')


def pytest_cmdline_main(config):
    storage = StorageManager(config.option.storage)
    config.pluginmanager.register(storage, "storage")


@pytest.fixture
def storage(request):
    store = request.config.pluginmanager.getplugin("storage")
    return store.get_storage(request.node)


@pytest.fixture(scope='session')
def pkgcache(request):
    store = request.config.pluginmanager.getplugin("storage")
    return store.join('pkgcache')
