import pytest
from lab.model import Environment
from unittests.mocks.lab import MockProvider


@pytest.fixture
def mock_environment():
    provider = MockProvider.mock({
        'dut': [
            'dut.example.com'
        ],
        'example': [
            'example1.example.com',
            'example2.example.com'
        ]
    })
    return Environment('pytest', [provider])


@pytest.fixture
def mock_provider(mock_environment):
    return mock_environment.layers[-1][1]


def test_presence(mock_environment):
    assert mock_environment.view['dut'] == ['dut.example.com']
    assert mock_environment.view['example'] == ['example1.example.com',
                                                'example2.example.com']


def test_register(mock_environment, mock_provider):
    mock_environment.register('test', 'test.example.com')
    assert mock_provider.asdict() == {
        'dut': [
            'dut.example.com'
        ],
        'example': [
            'example1.example.com',
            'example2.example.com'
        ],
        'test': [
            'test.example.com'
        ]
    }


def test_unregister(mock_environment, mock_provider):
    mock_environment.unregister('example', 'example1.example.com')
    assert mock_provider.asdict() == {
        'dut': [
            'dut.example.com'
        ],
        'example': [
            'example2.example.com'
        ]
    }

    mock_environment.unregister('example', 'example2.example.com')
    assert mock_provider.asdict() == {
        'dut': [
            'dut.example.com'
        ]
    }


def test_unregister_all(mock_environment, mock_provider):
    mock_environment.unregister('example')
    assert mock_provider.asdict() == {
        'dut': [
            'dut.example.com'
        ]
    }
