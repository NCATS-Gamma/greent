import requests
import pytest
import monitoring.swagger_based_test

robokop_host = 'http://robokop.renci.org'


@pytest.fixture()
def get_swagger_docs():
    spec = f'{robokop_host}:4868/openapi.json'
    return requests.get(spec).json()


@pytest.fixture()
def excluded_path():
    return [
        "https://robokop.renci.org/ranker/api/node_properties/",
        "https://robokop.renci.org/builder/api/predicates/",
    ]


def test_builder(get_swagger_docs, excluded_path):

    monitoring.swagger_based_test.test_endpoints(get_swagger_docs, excluded_path)
