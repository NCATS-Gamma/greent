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
# occured in the previous graph.  The new counts are stored for later use.  See test_rkg_counts.py
#
# The second component does some sanity checks to see that labels make sense.  This kind of stuff
# will mostly be subsumed into KGX at some point in the future, but for now is in this file
# (test_rkg_values.py)
#
###

# Get a driver to robokopdev
@pytest.fixture(scope="module")
def driver():
    url='bolt://robokopdev.renci.org:7687'
    auth=("neo4j", os.environ['NEO4J_PASSWORD'])
    return GraphDatabase.driver(url, auth=auth)


def query(driver,cypher):
    with driver.session() as session:
        results = session.run(cypher)
    return list(results)

def test_label_coherence(driver):
    """Make sure that our labels are biolink compliant.  Here, we hardcode valid label sets by hand."""
    validsets = set()
    validsets.add( frozenset(['named_thing','gene_or_gene_product','gene']) )
    validsets.add( frozenset(['named_thing','gene_or_gene_product','gene_product','chemical_substance']) )
    validsets.add( frozenset(['named_thing','chemical_substance']) )
    validsets.add( frozenset(['named_thing','biological_process_or_activity','biological_process']) )
    validsets.add( frozenset(['named_thing','biological_process_or_activity','biological_process','pathway']) )
    validsets.add( frozenset(['named_thing','biological_process_or_activity','molecular_activity']) )
    validsets.add( frozenset(['named_thing','anatomical_entity']) )
    validsets.add( frozenset(['named_thing','anatomical_entity','cellular_component']) )
    validsets.add( frozenset(['named_thing','anatomical_entity','cellular_component','cell']) )
    validsets.add( frozenset(['named_thing','disease_or_phenotypic_feature','disease']) )
    #Let's remove genetic condition?
    validsets.add( frozenset(['named_thing','disease_or_phenotypic_feature','disease','genetic_condition']) )
    validsets.add( frozenset(['named_thing','disease_or_phenotypic_feature','phenotypic_feature']) )
    validsets.add( frozenset(['named_thing','food']) )
    validsets.add( frozenset(['named_thing','sequence_variant']) )
    validsets.add( frozenset(['named_thing','gene_family']) )
    validsets.add( frozenset(['Concept']))
    labels = query(driver,'MATCH (a) return distinct labels(a) as l')
    ok = True
    for result in labels:
        labellist = frozenset(result['l'])
        if not labellist in validsets:
            print('Unusual label set:',labellist)
            ok = False
    assert ok

def test_no_unmapped_edges(driver):
    labels = query(driver,'MATCH (a)-[e:Unmapped_Relation]->(b) return count(distinct e) as c')
    assert labels[0]['c'] == 0

def test_no_unnamed_nodes(driver):
    labels = query(driver,'MATCH (a) where not exists(a.name) return count(distinct a) as c')
    assert labels[0]['c'] == 0

