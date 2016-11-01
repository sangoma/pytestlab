import pytest
from lab.model import Equipment
from unittests.mocks.lab import MockProvider


@pytest.fixture
def mock_location():
    provider = MockProvider.mock({
        'api-token': '992DF09BB8A353099C245D645468E4AB',
        'keyfile': 'id_rsa.pytest'
    })
    return Equipment('pytest', [provider])


@pytest.fixture
def mock_provider(mock_location):
    return mock_location.layers[-1][1]


def test_presence(mock_location):
    assert mock_location['api-token'] == '992DF09BB8A353099C245D645468E4AB'
    assert mock_location['keyfile'] == 'id_rsa.pytest'


def test_add_attribute(mock_location, mock_provider):
    mock_location['password'] = 'hunter2'
    assert mock_provider.asdict() == {
        'api-token': '992DF09BB8A353099C245D645468E4AB',
        'keyfile': 'id_rsa.pytest',
        'password': 'hunter2'
    }
