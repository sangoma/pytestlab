import collections
import logging
from pprint import pformat


class TooManyProviders(Exception):
    "Too many stores are enabled; can't write"


logger = logging.getLogger(__name__)


class ProvidersMixin(object):
    def __init__(self, name, providers, **kwargs):
        self.records = []
        self.name = name
        self.providers = providers
        self.kwargs = kwargs
        ident = self.modelid  # subclass defined
        logger.debug("Creating {} '{}'".format(ident, name))

        for store in providers:
            logger.debug("{}: reading {} '{}'".format(
                store.name, ident, self.name))
            record = store.get(ident, name, **self.kwargs)
            self.records.append((store, record))

        logger.debug("Records: {}".format(pformat(self.records)))

    def get_one(self):
        if len(self.records) > 1:
            raise TooManyProviders(self.records)

        # first (store, record) pair
        return self.records[0]


class Facts(collections.MutableMapping, ProvidersMixin):
    """A named map (usually an fqdn) of location specific "facts".
    """
    modelid = 'equipment'

    def __getitem__(self, key):
        return self.view[key]

    def __setitem__(self, key, value):
        _, record = self.get_one()
        data = record.data  # a copy
        data[key] = value
        record.push(data)

    def __delitem__(self, key):
        _, record = self.get_one()
        data = record.data  # a copy
        del data[key]
        record.push(data)

    def __iter__(self):
        return iter(self.view.keys())

    def __len__(self):
        return len(self.view.keys())

    @property
    def view(self):
        """A location mapping view across all facts providers.
        """
        facts_per_loc = collections.OrderedDict()
        for _, record in self.records:
            for location, facts in record.data.items():
                facts_per_loc[location] = facts

        return facts_per_loc


class Environment(ProvidersMixin):
    """A map of role names to lists of location specific ``Facts`` objects.
    """
    modelid = 'environment'

    def register(self, role, equip):
        """Register a role by mapping it to equipment
        """
        _, record = self.get_one()
        data = record.data

        try:
            roles = set(data[role])
            roles.add(equip)
            data[role] = list(roles)
        except KeyError:
            data[role] = [equip]

        record.push(data)

    def unregister(self, role, equip=None):
        """Unregister a role by unmapping it from equipment
        """
        _, record = self.get_one()
        data = record.data

        if equip:
            data[role].remove(equip)
            if not data[role]:
                del data[role]
        else:
            del data[role]
        record.push(data)

    def get(self, key, default=None):
        try:
            equipment = self[key]
        except KeyError:
            return default
        else:
            return equipment if equipment else default

    def __iter__(self):
        return iter(self.view)

    def __len__(self):
        return len(self.view)

    @property
    def view(self):
        """A role mapping view across all environment providers.
        """
        locsets = {}
        roles = {}
        for store, record in self.records:
            for rolename, locations in record.data.items():
                logger.debug("{}: found role '{}' -> {}"
                             .format(store.name, rolename, locations))

                # check for duplicates across providers
                locset = locsets.setdefault(rolename, set())
                for loc in locset:
                    if loc in locations:
                        logger.error(
                            "Discarding duplicate '{}' {} location '{}'"
                            .format(store.name, rolename, loc)
                        )
                        locations.remove(loc)

                locset.update(set(locations))

                roles.setdefault(
                    rolename, collections.OrderedDict()
                )[store.name] = locations

        return roles

    def __getitem__(self, role):
        equipment = []
        for _, locations in self.view[role].items():
            for location in locations:
                equipment.append(Facts(location, self.providers, role=role))

        return equipment
