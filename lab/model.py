import six
import json
import collections
import logging


logger = logging.getLogger(__name__)


def pretty_json(data):
    return six.text_type(json.dumps(data, indent=4, sort_keys=True,
                                    ensure_ascii=False))


class CommonMixin(object):
    def providers(self):
        for layer, data in reversed(self.layers):
            yield layer.name, data

    @property
    def view(self):
        data = {}
        for _, record in reversed(self.layers):
            data.update(record)
        return data


class Equipment(collections.MutableMapping, CommonMixin):
    def __init__(self, hostname, providers, **kwargs):
        self.layers = []
        self.hostname = hostname
        for backend in providers:
            provider = backend('equipment', hostname, **kwargs)
            data = json.loads(provider.data) if provider.data else {}
            self.layers.append((provider, data))

    def __getitem__(self, key):
        for _, data in self.layers:
            try:
                return data[key]
            except KeyError:
                pass
        raise KeyError(key)

    def __setitem__(self, key, value):
        provider, data = self.layers[-1]
        data[key] = value
        provider.push(pretty_json(data))

    def __delitem__(self, key):
        provider, data = self.layers[-1]
        del data[key]
        provider.push(pretty_json(data))

    def __iter__(self):
        return iter(self.view)

    def __len__(self):
        return len(self.view)


class Environment(CommonMixin):
    def __init__(self, name, providers, **kwargs):
        self.layers = []
        self._providers = providers
        self._kwargs = kwargs

        for backend in providers:
            provider = backend('environment', name, **kwargs)
            data = json.loads(provider.data) if provider.data else {}
            self.layers.append((provider, data))

    def register(self, role, eq):
        provider, data = self.layers[-1]

        try:
            roles = set(data[role])
            roles.add(eq)
            data[role] = list(roles)
        except KeyError:
            data[role] = [eq]

        provider.push(pretty_json(data))

    def unregister(self, role, eq=None):
        provider, data = self.layers[-1]

        if eq:
            data[role].remove(eq)
            if not data[role]:
                del data[role]
        else:
            del data[role]
        provider.push(pretty_json(data))

    def __getitem__(self, key):
        return [Equipment(x, self._providers, **self._kwargs)
                for x in self.view[key]]

    def get(self, key, default=None):
        try:
            return self[key]
        except IndexError:
            return default

    def __iter__(self):
        return iter(self.view)

    def __len__(self):
        return len(self.view)
