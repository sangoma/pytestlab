import pytest
from lab.model import Facts
from unittests.mocks.lab import MockProvider


@pytest.fixture
def mock_location():
    provider = MockProvider.mock({
        'api-token': '992DF09BB8A353099C245D645468E4AB',
        'keyfile': 'id_rsa.pytest'
    })
    return Facts('pytest', [provider])


@pytest.fixture
def mock_provider(mock_location):
    return mock_location.get_one()[0]


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
