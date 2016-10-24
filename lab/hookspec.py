import pytest


@pytest.hookspec(historic=True)
def pytest_lab_addroles(rolemanager):
    """new role registered"""


# TODO: Hook for publishing new role **should not** be historic - this
# no longer makes sense. Roles can now disappear before the historic
# hook can be triggered. Any plugin that cares about having a complete
# canonical list of roles should talk directly to the role manager
# instead.
@pytest.hookspec(historic=True)
def pytest_lab_role_created(config, ctl):
    """Called when a new role controller is created (and loaded) at a
    location.
    """


def pytest_lab_role_destroyed(config, ctl):
    """Called when a role controller is destroyed.
    """
