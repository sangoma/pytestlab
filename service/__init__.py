import sys
import csv
import hug
from frozendict import frozendict
from collections import defaultdict


def _load_marks(filename):
    data = defaultdict(set)

    with open(filename, 'r') as csvfile:
        reader = csv.reader(csvfile)
        for key, value in reader:
            data[key].add(value)

    return frozendict(data)


# Load our CSV and import time
_markdata = _load_marks(sys.argv[-1])


def is_marked(env, name):
    markdata = _markdata.get(env)
    return markdata and name in markdata


@hug.get('/mark')
def get(env: hug.types.text, name: hug.types.text):
    response =  []
    if is_marked(env, name):
        response.append({
            'name': 'skip',
            'args': {'reason': 'Skipping known broken'},
        })
    return response
