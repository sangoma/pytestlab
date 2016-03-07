import os
import io
import errno
from xdg import BaseDirectory
from .common import ProviderError


class Record(object):
    def __init__(self, *path):
        data_dir = BaseDirectory.save_data_path('lab', 'v1', *path[:-1])
        self.path = os.path.join(data_dir, path[-1])

        try:
            with io.open(self.path, 'r') as fp:
                self.data = fp.read()
        except IOError as e:
            if e.errno == errno.ENOENT:
                self.data = None
            else:
                raise ProviderError(e)

    def push(self, data):
        with io.open(self.path, 'w', encoding='utf-8') as fp:
            return fp.write(data)


class FileProvider(object):
    name = 'files'

    def __init__(self, config):
        pass

    def get(self, *path):
        return Record(*path)
