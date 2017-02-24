#
# Copyright 2017 Sangoma Technologies Inc.
#
import json
import six


__all__ = ['ProviderError']


class ProviderError(Exception):
    pass


def pretty_json(data):
    return six.text_type(json.dumps(data, indent=4, sort_keys=True,
                                    ensure_ascii=False))
