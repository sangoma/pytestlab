import operator
from cliff.command import Command


class Importer(Command):
    "manage facts for machines"

    def get_parser(self, prog_name):
        parser = super(Importer, self).get_parser(prog_name)
        parser.add_argument('source', type=str)
        parser.add_argument('type', type=str)
        parser.add_argument('name', type=str)
        return parser

    def take_action(self, parsed_args):
        if parsed_args.source != 'pycopia':
            raise ValueError("Unsupported importer".format(type))

        from lab import pycopia

        db = pycopia.Importer(self.app.config['pycopia']['database'])
        if parsed_args.type == 'environment':
            entry = self.app.get_environment(parsed_args.name)
            for roles in db.environments(parsed_args.name).itervalues():
                for role, hostname in roles.iteritems():
                    entry.register(pycopia.normalize_role(role),
                                   pycopia.normalize_hostnames(hostname))
        elif parsed_args.type == 'equipment':
            entry = self.app.get_equipment(parsed_args.name)
            for key, value in db.equipment(parsed_args.name).iteritems():
                entry[key] = value
        else:
            raise ValueError("Unsupported type {}".format(type))
