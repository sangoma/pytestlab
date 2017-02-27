#
# Copyright 2017 Sangoma Technologies Inc.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import json
import six


__all__ = ['ProviderError']


class ProviderError(Exception):
    pass


def pretty_json(data):
    return six.text_type(json.dumps(data, indent=4, sort_keys=True,
                                    ensure_ascii=False))
