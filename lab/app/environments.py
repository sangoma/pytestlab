#
# Copyright 2017 Sangoma Technologies Inc.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import logging
from cliff.lister import Lister


def get_items(cmd, parsed_args, entry):
    entry = entry
    header = ('role',) + tuple(
        "hosts @ {}".format(provider.name)
        for provider in entry.providers
    )
    rows = []
    for rolename, locs_per_provider in entry.view.items():
        row = [rolename]
        for provider in entry.providers:
            row.append(', '.join(locs_per_provider.get(
                provider.name, ('',))))
        rows.append(row)

    return (header, rows)


class EnvLister(Lister):
    "Show an environment"
    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(EnvLister, self).get_parser(prog_name)
        parser.add_argument('name', type=str, help='environment name')
        return parser

    def take_action(self, parsed_args):
        entry = self.app.get_environment(parsed_args.name)
        if not entry.view:
            self.log.warn("The environment '{}' is not defined by any provider"
                          .format(entry.name))
        return get_items(self, parsed_args, entry)


class EnvRegister(Lister):
    "Register a role to an environment"

    def get_parser(self, prog_name):
        parser = super(EnvRegister, self).get_parser(prog_name)
        parser.add_argument('name', type=str, help='environment name')
        parser.add_argument('role', type=str, help='role to register as')
        parser.add_argument('host', type=str, help='hostname to register')
        return parser

    def take_action(self, parsed_args):
        entry = self.app.get_environment(parsed_args.name)
        entry.register(parsed_args.role, parsed_args.host)
        return get_items(self, parsed_args, entry)


class EnvUnregister(Lister):
    "Unregister a role from an environment"

    def get_parser(self, prog_name):
        parser = super(EnvUnregister, self).get_parser(prog_name)
        parser.add_argument('name', type=str, help='environment name')
        parser.add_argument('role', type=str, help='role to unregister')
        parser.add_argument('host', nargs='?', type=str,
                            help='specific hostname to unregister')
        return parser

    def take_action(self, parsed_args):
        entry = self.app.get_environment(parsed_args.name)
        entry.unregister(parsed_args.role, parsed_args.host)
        return get_items(self, parsed_args, entry)
