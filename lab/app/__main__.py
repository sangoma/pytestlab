import sys
from cliff.app import App
from cliff.commandmanager import CommandManager
from lab.provider import get_providers
from lab.model import Environment, Equipment
from lab.config import load_lab_config


class LabctlApp(App):
    def __init__(self):
        self.config = load_lab_config()
        assert self.config, 'No config file (lab.yaml) could be found?'
        self.providers = None
        super(LabctlApp, self).__init__(
            description='Manage pytest-lab',
            version='0.1',
            command_manager=CommandManager('labctl'),
            deferred_help=True
        )

    def initialize_app(self, argv):
        self.providers = get_providers('postgresql, files', self.config)

    def get_equipment(self, name):
        return Equipment(name, self.providers)

    def get_environment(self, name):
        return Environment(name, self.providers)


def main(argv=sys.argv[1:]):
    myapp = LabctlApp()
    return myapp.run(argv)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
