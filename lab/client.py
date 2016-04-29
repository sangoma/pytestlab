import io
import sys
import click
import logging
import os

from provider import FileProvider, EtcdProvider, PostgresqlProvider
from model import Environment, Equipment, pretty_json
from config import load_lab_config


logger = logging.getLogger(__name__)


def load_backends(config=None):
    if not config:
        config = load_lab_config().get('providers')

    backends = []
    for node in config:
        name, kwargs = node.items()[0]
        backend = Client.BACKENDS[name](kwargs)
        backends.append(backend)
    return backends


class Client(object):
    BACKENDS = {backend.name: backend
                for backend in [FileProvider, EtcdProvider,
                                PostgresqlProvider]}

    def __init__(self, targets):
        self.config = load_lab_config()

        backends_config = self.config.get('providers')
        if not backends_config:
            if targets:  # parse `targets` comma separated str
                targets_set = set(x.strip() for x in targets.split(','))
                backends_config = [{target: None} for target in targets_set]
            else:
                backends_config = [{'files': None}]

        self.providers = load_backends(backends_config)

    def equipment(self, name):
        return Equipment(name, self.providers)

    def environment(self, name):
        return Environment(name, self.providers)

    def print_entry(self, entry, verbose):
        report = io.StringIO()
        if verbose:
            for name, data in entry.providers():
                report.write(u'{}:\n'.format(name))
                report.write(pretty_json(data))
                report.write(u'\n')
        else:
            report.write(pretty_json(entry.view))

        click.echo_via_pager(report.getvalue())


pass_client = click.make_pass_decorator(Client)


@click.group()
@click.option('--targets', '-t', metavar='TARGETS[,...]',
              help='The data providers to query, comma separated')
@click.option('--loglevel', '-l', metavar='LEVEL',
              help='Explicitly set the python logging level')
@click.option('-v', '--verbose', count=True,
              help='Verbosity level. Pass more then once to increase the '
                   ' logging level')
@click.pass_context
def cli(ctx, targets, loglevel, verbose):
    # pager options
    os.environ['LESS'] = 'FRSX'
    # explicit level always overrides
    logging.basicConfig(
        level=loglevel.upper() if loglevel else max(40 - verbose * 10, 10)
    )
    ctx.obj = Client(targets)


@cli.group(help='Manipulate information on lab equipment')
@click.argument('name')
@click.pass_context
def equipment(ctx, name):
    ctx.name = name


@equipment.command('get')
@click.option('--verbose', '-v', is_flag=True)
@pass_client
@click.pass_context
def equipment_get(ctx, client, verbose):
    name = ctx.parent.name
    entry = client.equipment(name)

    if not entry:
        click.echo_via_pager("No equipment '{}' was found".format(name))
        return
    client.print_entry(entry, verbose)


@equipment.command('set')
@click.argument('key')
@click.argument('value')
@pass_client
@click.pass_context
def equipment_set(ctx, client, key, value):
    entry = client.equipment(ctx.parent.name)

    entry[key] = value
    client.print_entry(entry, True)


@equipment.command('rm')
@click.argument('key', required=False)
@pass_client
@click.pass_context
def equipment_rm(ctx, client, key):
    entry = client.equipment(ctx.parent.name)

    if key and key in entry:
        del entry[key]
        client.print_entry(entry, True)
    else:
        entry.clear()


@cli.group(help='Manipulate and define lab environments')
@click.argument('name')
@click.pass_context
def env(ctx, name):
    ctx.name = name


@env.command('get')
@click.option('--verbose', '-v', is_flag=True)
@pass_client
@click.pass_context
def env_get(ctx, client, verbose):
    name = ctx.parent.name
    entry = client.environment(name)

    if not entry:
        click.echo_via_pager("No environment '{}' was found".format(name))
        return

    client.print_entry(entry, verbose)


@env.command('register')
@click.argument('role')
@click.argument('eq')
@pass_client
@click.pass_context
def env_register(ctx, client, role, eq):
    entry = client.environment(ctx.parent.name)

    entry.register(role, eq)
    client.print_entry(entry, True)


@env.command('unregister')
@click.argument('role')
@click.argument('eq', required=False)
@pass_client
@click.pass_context
def env_unregister(ctx, client, role, eq):
    entry = client.environment(ctx.parent.name)

    entry.unregister(role, eq)
    client.print_entry(entry, True)


@cli.command('import', help='Import data from external sources')
@click.argument('source')
@click.argument('type')
@click.argument('name')
@pass_client
def import_data(client, source, type, name):
    if source != 'pycopia':
        click.echo('Unsupported importer', file=sys.stderr)
        sys.exit(1)

    import pycopia

    db = pycopia.Importer(client.config['pycopia']['database'])
    if type == 'environment':
        entry = client.environment(name)
        for roles in db.environments(name).itervalues():
            for role, hostname in roles.iteritems():
                entry.register(pycopia.normalize_role(role),
                               pycopia.normalize_hostnames(hostname))
    elif type == 'equipment':
        entry = client.equipment(name)
        for key, value in db.equipment(name).iteritems():
            entry[key] = value
    else:
        click.echo("Unsupported type {}".format(type), file=sys.stderr)
        sys.exit(1)

    client.print_entry(entry, True)


if __name__ == '__main__':
    cli()
