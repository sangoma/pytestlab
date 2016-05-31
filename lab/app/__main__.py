import sys
from cliff.app import App
from cliff.commandmanager import CommandManager
from lab.provider import FileProvider, EtcdProvider, PostgresqlProvider
from lab.model import Environment, Equipment
from lab.config import load_lab_config


BACKENDS = {backend.name: backend
            for backend in [FileProvider, EtcdProvider,
                            PostgresqlProvider]}


def load_backends(config=None):
    if not config:
        config = load_lab_config().get('providers')

    backends = []
    for node in config:
        name, kwargs = node.items()[0]
        backend = BACKENDS[name](kwargs)
        backends.append(backend)
    return backends


def get_providers(targets, config):
    backends_config = config.get('providers')
    if not backends_config:
        if targets:  # parse `targets` comma separated str
            targets_set = set(x.strip() for x in targets.split(','))
            backends_config = [{target: None} for target in targets_set]
        else:
            backends_config = [{'files': None}]

    return load_backends(backends_config)


class LabctlApp(App):
    def __init__(self):
        self.config = load_lab_config()
        self.providers = None
        super(LabctlApp, self).__init__(
            description='Manage pytest-lab',
            version='0.1',
            command_manager=CommandManager('labctl'),
            deferred_help=True
        )

    def initialize_app(self, argv):
        self.providers = get_providers('postgresql', self.config)

    def get_equipment(self, name):
        return Equipment(name, self.providers)

    def get_environment(self, name):
        return Environment(name, self.providers)


def main(argv=sys.argv[1:]):
    myapp = LabctlApp()
    return myapp.run(argv)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
