import os
import pytest
import redis


@pytest.fixture
def redis_main_cache_client():
    return redis.Redis(host = os.environ.get('CACHE_HOST'), password= os.environ.get('CACHE_PASSWORD'), port = os.environ.get('CACHE_PORT'))



def test_redis_up(redis_main_cache_client):
    echo_string = 'Hi redis'
    assert redis_main_cache_client.echo(echo_string).decode('utf-8') == echo_string

def test_redis_has_data(redis_main_cache_client):
    assert redis_main_cache_client.dbsize() > 0

