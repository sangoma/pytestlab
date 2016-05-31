import operator
from cliff.lister import Lister


class FactsLister(Lister):
    "manage facts for machines"

    def get_parser(self, prog_name):
        parser = super(FactsLister, self).get_parser(prog_name)
        parser.add_argument('host', type=str, help='environment name')
        parser.add_argument('key', nargs='?', type=str)
        parser.add_argument('value', nargs='?', type=str)
        parser.add_argument('--unset', action='store')
        parser.add_argument('--unset-all', action='store_true')
        return parser

    def take_action(self, parsed_args):
        entry = self.app.get_equipment(parsed_args.host)

        if parsed_args.unset:
            del entry[parsed_args.unset]
        elif parsed_args.unset_all:
            entry.clear()
        elif parsed_args.key and parsed_args.value:
            entry[parsed_args.key] = parsed_args.value

        items = sorted(entry.view.iteritems(), key=operator.itemgetter(0))
        return ('key', 'value'), items
