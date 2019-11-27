import os
import redis
import pytest


@pytest.fixture()
def redis_connection():
    return redis.Redis(
        host=os.environ['PUBMED_CACHE_HOST'],
        port=os.environ['PUBMED_CACHE_PORT'],
        password=os.environ['PUBMED_CACHE_PASSWORD']
    )


def test_pubmed_cache_up(redis_connection):
    """
    Tests if pubmed cache is up
    :param redis_connection:
    :return:
    """
    echo_string = 'hi redis'
    assert redis_connection.echo(echo_string).decode('utf-8') == echo_string


