import pytest
import os
from collections import defaultdict
import json
from neo4j.v1 import GraphDatabase

###
#
# Test module for a newly built robokop KG.
#
# Has 2 components. In one, we compare the numbers of different kinds of edges to those that
# occured in the previous graph.  The new counts are stored for later use.  This test file
# (test_rkg_counts.py) covers this case.
#
# The second component does some sanity checks to see that labels make sense.  This kind of stuff
# will mostly be subsumed into KGX at some point in the future, but for now is in test_rkg_values.py
#
###

# Get a driver to robokopdev
@pytest.fixture(scope="module")
def driver():
    url='bolt://robokopdev.renci.org:7687'
    auth=("neo4j", os.environ['NEO4J_PASSWORD'])
    return GraphDatabase.driver(url, auth=auth)

def get_most_recent(currdir, sname):
    files = os.listdir(currdir)
    prev_stats = list(filter(lambda x: x.startswith(sname), files))
    return len(prev_stats)-1

def get_prev(sname):
    currdir = os.path.join(os.path.dirname(os.path.abspath(__file__)),'kgstats')
    most_recent = get_most_recent(currdir, sname)
    files = os.listdir(currdir)
    prev_stats = list(filter(lambda x: x.startswith(sname), files))
    most_recent = len(prev_stats)-1
    if most_recent == -1:
        return defaultdict(int)
    fname = f'{sname}.{most_recent}'
    with open(os.path.join(currdir,fname),'r') as jsonfile:
        prev_data = json.load(jsonfile)
    return prev_data

def write_data(sname,outdata):
    currdir = os.path.join(os.path.dirname(os.path.abspath(__file__)),'kgstats')
    most_recent = get_most_recent(currdir,sname)
    next = most_recent + 1
    fname = f'{sname}.{next}'
    with open(os.path.join(currdir,fname),'w') as jsonfile:
        json.dump(outdata,jsonfile)

def query(driver,cypher):
    with driver.session() as session:
        results = session.run(cypher)
    return list(results)

def test_node_labels(driver):
    prev_nodes = get_prev('nodedata')
    labels = query(driver,'MATCH (a) return distinct labels(a) as l, count(*) as c')
    increased = False
    outdata = {}
    for result in labels:
        labellist = result['l']
        labellist.sort()
        key= ','.join(labellist)
        current_count = result['c']
        previous_count = prev_nodes[key]
        assert(current_count >= previous_count)
        outdata[key] = current_count
        if current_count > previous_count:
            increased=True
    if increased:
        write_data('nodedata',outdata)
        print('write')

def test_edge_labels(driver):
    name = 'edgelabels'
    prev_nodes = get_prev(name)
    labels = query(driver,'match (a)-[x]->(b) return distinct type(x) as l, count(*) as c')
    increased = False
    outdata = {}
    for result in labels:
        key = result['l']
        current_count = result['c']
        previous_count = prev_nodes[key]
        assert(current_count >= previous_count)
        outdata[key] = current_count
        if current_count > previous_count:
            increased=True
    if increased:
        write_data(name,outdata)
        print('write')

def test_edge_sources(driver):
    name = 'edgesources'
    prev_nodes = get_prev(name)
    labels = query(driver,'match (a)-[x]->(b) unwind x.source_database as l return distinct l, count(*) as c')
    increased = False
    outdata = {}
    for result in labels:
        key = result['l']
        current_count = result['c']
        previous_count = prev_nodes[key]
        assert(current_count >= previous_count)
        outdata[key] = current_count
        if current_count > previous_count:
            increased=True
    if increased:
        write_data(name,outdata)
        print('write')


def test_nn(driver):
    name = 'node_node'
    prev_edges = get_prev(name)
    labels = query(driver,'MATCH (a)-->(b) return distinct labels(a) as la, labels(b) as lb, count(*) as c')
    increased = False
    outdata = {}
    for result in labels:
        sourcelabellist = result['la']
        sourcelabellist.sort()
        sourcekey= ','.join(sourcelabellist)
        targetlabellist = result['lb']
        targetlabellist.sort()
        targetkey = ','.join(targetlabellist)
        key = sourcekey+"+"+targetkey
        current_count = result['c']
        previous_count = prev_edges[key]
        assert(current_count >= previous_count)
        outdata[key] = current_count
        if current_count > previous_count:
            increased=True
    if increased:
        write_data(name,outdata)
        print('write')

