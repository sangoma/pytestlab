"""
Config file management
"""
import py.path
import yaml


def load_yaml_config():
    """Load data from the file lab.yaml.

    Start looking in the PWD and return the first file found by successive
    upward steps in the file system.
    """
    path = py.path.local()
    for basename in path.parts(reverse=True):
        configfile = basename.join('lab.yaml')
        if configfile.check():
            return yaml.load(configfile.read())
    return {}
