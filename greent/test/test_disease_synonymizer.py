from greent.graph_components import KNode
from greent.synonymizers.disease_synonymizer import synonymize
from greent.conftest import rosetta
from greent import node_types
from greent.util import Text


def test_mondo_synonymization(rosetta):
    """Start at the MONDO node for Niemann Pick Disease, look for other identifiers, including 
    DOID and MeSH"""
    #Niemann Pick Disease (not type C)
    node = KNode('MONDO:0001982', type=node_types.DISEASE)
    synonyms = synonymize(node,rosetta.core)
    assert len(synonyms) > 5
    node.add_synonyms(synonyms)
    doids = node.get_synonyms_by_prefix('DOID')
    assert len(doids) == 1
    assert doids.pop() == 'DOID:14504'
    meshes = node.get_synonyms_by_prefix('MESH')
    assert len(meshes) == 1
    assert 'MeSH:D009542' in meshes
    assert Text.get_curie(node.id) == 'MONDO'
    #This is not really what the synonymizer does.  The synonymizer returns synonyms, not modifies the node.
    #assert node.name == 'Niemann-Pick Disease'

def test_mondo_synonymization_2(rosetta):
    """Given the MONDO for Ebola, make sure that we get back a DOID and a MESH"""
    node = KNode('MONDO:0005737', type=node_types.DISEASE)
    synonyms = synonymize(node,rosetta.core)
    assert len(synonyms) > 1
    node.add_synonyms(synonyms)
    doids = node.get_synonyms_by_prefix('DOID')
    assert len(doids) == 1
    meshes = node.get_synonyms_by_prefix('MESH')
    assert len(meshes) > 0
    assert Text.get_curie(node.id) == 'MONDO'

def test_disease_normalization(rosetta):
    """Given the DOID for Ebola, make sure that we get back a DOID and a MESH.
    Calling through rosetta also normalizes, unlike the tests above"""
    node = KNode('DOID:4325', type=node_types.DISEASE)
    rosetta.synonymizer.synonymize(node)
    mondos = node.get_synonyms_by_prefix('MONDO')
    assert len(mondos) > 0
    assert Text.get_curie(node.id) == 'MONDO'
