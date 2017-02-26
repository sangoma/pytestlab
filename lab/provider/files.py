#
# Copyright 2017 Sangoma Technologies Inc.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from builtins import object
import os
import io
import errno
import json
from xdg import BaseDirectory
from .common import ProviderError, pretty_json


class Record(object):
    def __init__(self, *path):
        data_dir = BaseDirectory.save_data_path('lab', 'v1', *path[:-1])
        self.path = os.path.join(data_dir, path[-1])

    @property
    def data(self):
        try:
            with io.open(self.path, 'r') as fp:
                return json.loads(fp.read())
        except IOError as e:
            if e.errno == errno.ENOENT:
                return {}
            else:
                raise ProviderError(e)
        except ValueError:  # no json to read
            return {}

    def push(self, data):
        with io.open(self.path, 'w', encoding='utf-8') as fp:
            return fp.write(pretty_json(data))


class FileProvider(object):
    name = 'files'

    def __init__(self, config):
        # We don't support and configuration, so intentionally empty
        pass

    def get(self, *path, **kwargs):
        return Record(*path)
