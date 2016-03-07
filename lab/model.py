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
        for name, layer, data in reversed(self.layers):
            yield name, data

    @property
    def view(self):
        """A copy of this provider's data contents.
        """
        data = {}
        for _, _, record in reversed(self.layers):
            data.update(record)
        return data


class Equipment(collections.MutableMapping, CommonMixin):
    def __init__(self, hostname, providers):
        self.layers = []
        self.hostname = hostname
        for backend in providers:
            logger.debug("reading equipment {} from "
                         "{}".format(hostname, backend.name))

            provider = backend.get('equipment', hostname)
            data = json.loads(provider.data) if provider.data else {}
            self.layers.append((backend.name, provider, data))

    def __getitem__(self, key):
        for _, _, data in self.layers:
            try:
                return data[key]
            except KeyError:
                pass
        raise KeyError(key)

    def __setitem__(self, key, value):
        _, provider, data = self.layers[-1]
        data[key] = value
        provider.push(pretty_json(data))

    def __delitem__(self, key):
        _, provider, data = self.layers[-1]
        del data[key]
        provider.push(pretty_json(data))

    def __iter__(self):
        return iter(self.view)

    def __len__(self):
        return len(self.view)


class Environment(CommonMixin):
    def __init__(self, name, providers):
        self.layers = []
        self._providers = providers

        for backend in providers:
            logger.debug("reading environment {} from "
                         "{}".format(name, backend.name))

            provider = backend.get('environment', name)
            data = json.loads(provider.data) if provider.data else {}
            self.layers.append((backend.name, provider, data))

    def register(self, role, eq):
        """Register a role by mapping it to equipment
        """
        _, provider, data = self.layers[-1]

        try:
            roles = set(data[role])
            roles.add(eq)
            data[role] = list(roles)
        except KeyError:
            data[role] = [eq]

        provider.push(pretty_json(data))

    def unregister(self, role, eq=None):
        """Unregister a role by unmapping it from equipment
        """
        _, provider, data = self.layers[-1]

        if eq:
            data[role].remove(eq)
            if not data[role]:
                del data[role]
        else:
            del data[role]
        provider.push(pretty_json(data))

    def __getitem__(self, key):
        return [Equipment(x, self._providers) for x in self.view[key]]

    def get(self, key, default=None):
        try:
            return self[key]
        except IndexError:
            return default

    def __iter__(self):
        return iter(self.view)

    def __len__(self):
        return len(self.view)
