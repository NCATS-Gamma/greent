import os
import psycopg2
import pytest

@pytest.fixture()
def db_connection():
    return psycopg2.connect(
            dbname=os.environ['OMNICORP_DB'],
            user=os.environ['OMNICORP_USER'],
            host=os.environ['OMNICORP_HOST'],
            port=os.environ['OMNICORP_PORT'],
            password=os.environ['OMNICORP_PASSWORD'])

@pytest.fixture()
def tables(db_connection):
    query = """SELECT * FROM 
                information_schema.tables
                WHERE table_schema = 'omnicorp'"""
    cur = db_connection.cursor()
    cur.execute(query)
    tables = cur.fetchall()
    cur.close()
    return list(map(lambda y: '.'.join(y),list(map(lambda x: x[:3], tables))))




def test_tables(tables):
    """
    Test makes sure to see if tables are defined in omnicorp db
    """
    assert tables


def test_every_table_has_something(tables, db_connection):
    """
    Test for making sure every table has somethimg in it.
    """
    cursor = db_connection.cursor()
    query = lambda table_name: f"""
        SELECT COUNT(*) 
        FROM {table_name};
    """

    for table in tables:
        cursor.execute(query(table))
        count = cursor.fetchall()[0][0]
        assert int(count) > 0
    cursor.close()


