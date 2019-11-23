import pytest
import os
from neo4j.v1 import GraphDatabase


# Get a driver to robokopdev
@pytest.fixture(scope="module")
def driver():
    url='bolt://robokopdev.renci.org:7687'
    auth=("neo4j", os.environ['NEO4J_PASSWORD'])
    return GraphDatabase.driver(url, auth=auth)

#Return counts of nodes by label as a fixture to make tests more discrete
@pytest.fixture(scope="module")
def labels(driver):
    return query(driver,'MATCH (a) return distinct labels(a), count(*)')

def query(driver,cypher):
    with driver.session() as session:
        results = session.run(cypher)
    return list(results)

#The min count is somewhat arbitrary.
# After each rebuild where we add nodes, we should maybe increase?
#The goal is to make sure that we're not missing nodes
def test_node_count(driver):
    results = query(driver,'MATCH (a) return count(distinct a)')
    print(results)
    assert results[0][0] > 2600000

def test_node_labels(labels):
    for result in labels:
        print(result)

#This test is rather slow
def test_edge_count(driver):
    results = query(driver,'MATCH (a)-[x]->(b) return count(distinct x)')
    print(results)
    #This number is somewhat arbitrary.   After each rebuild where we add edges, we should maybe increase?
    assert results[0][0] > 10000000

