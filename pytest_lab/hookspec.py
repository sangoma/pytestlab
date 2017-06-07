#
# Copyright 2017 Sangoma Technologies Inc.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import pytest


@pytest.hookspec(historic=True)
def pytest_lab_map(config, roles):
    pass


@pytest.hookspec(firstresult=True)
def pytest_lab_load_role(config, identifier, facts):
    pass


@pytest.hookspec(firstresult=True)
def pytest_lab_dispatch(config, identifier):
    pass


def pytest_lab_aquire_lock(config, identifier):
    pass


def pytest_lab_release_lock(config, identifier):
    pass


@pytest.hookspec(firstresult=True)
def pytest_lab_getcfg(config, filenames):
    pass


@pytest.hookspec
def pytest_lab_configure(envmanager):
    """pytestlab startup"""


@pytest.hookspec(historic=True)
def pytest_lab_addroles(config, rolemanager):
    """new role registered"""


# TODO: Hook for publishing new role **should not** be historic - this
# no longer makes sense. Roles can now disappear before the historic
# hook can be triggered. Any plugin that cares about having a complete
# canonical list of roles should talk directly to the role manager
# instead.
@pytest.hookspec(historic=True)
def pytest_lab_role_created(config, name, role):
    """Called when a new role controller is created (and loaded) at a
    location.
    """


@pytest.hookspec
def pytest_lab_role_destroyed(config, role):
    """Called when a role controller is destroyed.
    """


@pytest.hookspec
def pytest_lab_location_destroyed(config, location):
    """Called when a location is released by the environment manager.
    """


@pytest.hookspec
def pytest_lab_add_providers(config, providermanager):
    """Called to enable adding addtional/external environment providers.
    """

@pytest.hookspec(firstresult=True)
def pytest_lab_get_storage(item):
    pass
