import pytest
from lab.model import Environment


@pytest.fixture
def mock_environment(mock_provider):
    return Environment('pytest', [mock_provider])


@pytest.fixture
def mock_record(mock_environment):
    return mock_environment.get_one()[0]


def test_presence(mock_environment):
    assert mock_environment.view['dut']['mock'] == ['dut.example.com']
    assert mock_environment.view['example']['mock'] == [
        'example1.example.com', 'example2.example.com']


def test_register(mock_environment, mock_record):
    mock_environment.register('test', 'test.example.com')
    assert mock_record.asdict() == {
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


def test_unregister(mock_environment, mock_record):
    mock_environment.unregister('example', 'example1.example.com')
    assert mock_record.asdict() == {
        'dut': [
            'dut.example.com'
        ],
        'example': [
            'example2.example.com'
        ]
    }

    mock_environment.unregister('example', 'example2.example.com')
    assert mock_record.asdict() == {
        'dut': [
            'dut.example.com'
        ]
    }


def test_unregister_all(mock_environment, mock_record):
    mock_environment.unregister('example')
    assert mock_record.asdict() == {
        'dut': [
            'dut.example.com'
        ]
    }
