import requests
import pytest
import monitoring.swagger_based_test

robokop_host = 'https://robokop.renci.org'


@pytest.fixture()
def get_swagger_docs():
    spec = f'{robokop_host}/apispec_1.json'
    return requests.get(spec).json()


@pytest.fixture()
def excluded_path():
    return [
        'https://robokop.renci.org/api/a/',
        'https://robokop.renci.org/api/q',
        'https://robokop.renci.org/api/t',
        'https://robokop.renci.org/api/simple/quick',
        'https://robokop.renci.org/api/neighborhood/',
        'https://robokop.renci.org/api/details/'
    ]


def test_manager(get_swagger_docs, excluded_path):
    monitoring.swagger_based_test.test_endpoints(get_swagger_docs, excluded_path)
