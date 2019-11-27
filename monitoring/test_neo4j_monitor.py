from neo4j import GraphDatabase
import pytest
import os
import requests
import base64


@pytest.fixture()
def db_driver():
    return GraphDatabase.driver(uri=f"bolt://{os.environ.get('NEO4J_HOST')}:{os.environ.get('NEO4J_BOLT_PORT')}", auth=('neo4j', os.environ['NEO4J_PASSWORD']))

@pytest.fixture()
def neo_http_host():
    return f"http://{os.environ.get('NEO4J_HOST')}:{os.environ.get('NEO4J_HTTP_PORT')}"

@pytest.fixture()
def credentials_for_http():
    formatted = f'neo4j:{os.environ["NEO4J_PASSWORD"]}'
    return base64.b64encode(formatted.encode()).decode()

@pytest.fixture()
def neo_https_host():
    return f"https://{os.environ.get('NEO4J_HOST')}:{os.environ.get('NEO4J_HTTPS_PORT')}"

@pytest.fixture()
def headers(credentials_for_http):
    c = credentials_for_http
    return {
        'Accept': 'application/json; charset=UTF-8',
        'Authorization': f'Basic {c}'
    }

def test_bolt(db_driver):
    query = 'MATCH (c) return count(c)'
    with db_driver.session() as session:
        result = session.run(query).single()
    assert result


def test_http(neo_http_host, headers):
    url = f"{neo_http_host}/db/data"
    errors = requests.get(
        url= url,
        headers = headers
    ).json().get('errors',[])
    assert errors == []

def test_https(neo_https_host, headers):
    url = f'{neo_https_host}/db/data'
    errors = requests.get(
        url= url,
        headers = headers
    ).json().get('errors', [])
    assert errors == []