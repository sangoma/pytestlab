import py.path
import yaml


def load_lab_config():
    path = py.path.local()
    for basename in path.parts(reverse=True):
        configfile = basename.join('lab.yaml')
        if configfile.check():
            return yaml.load(configfile.read())
    return {}
