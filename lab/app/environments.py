import operator
from cliff.command import Command
from cliff.lister import Lister


class EnvLister(Lister):
    "show an environment"

    def get_parser(self, prog_name):
        parser = super(EnvLister, self).get_parser(prog_name)
        parser.add_argument('name', type=str, help='environment name')
        return parser

    def take_action(self, parsed_args):
        entry = self.app.get_environment(parsed_args.name)
        items = sorted(entry.view.iteritems(), key=operator.itemgetter(0))
        return (('role', 'hosts'),
                ((role, ','.join(hosts)) for role, hosts in items))


class EnvRegister(Command):
    "register a role to an environment"

    def get_parser(self, prog_name):
        parser = super(EnvRegister, self).get_parser(prog_name)
        parser.add_argument('name', type=str, help='environment name')
        parser.add_argument('role', type=str, help='role to register as')
        parser.add_argument('host', type=str, help='hostname to register')
        return parser

    def take_action(self, parsed_args):
        entry = self.app.get_environment(parsed_args.name)
        entry.register(parsed_args.role, parsed_args.host)


class EnvUnregister(Command):
    "unregister a role from an environment"

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
