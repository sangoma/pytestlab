import os
import io
import errno
import logging

from xdg import BaseDirectory
from .common import ProviderError

log = logging.getLogger(__name__)


class FileProvider(object):
    name = 'files'

    def __init__(self, *path, **kwargs):
        data_dir = BaseDirectory.save_data_path('lab', 'v1', *path[:-1])
        self.path = os.path.join(data_dir, path[-1])
        log.debug("reading from {} with {}".format(
            self.path, type(self).__name__))

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
