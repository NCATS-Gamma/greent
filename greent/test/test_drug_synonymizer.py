from greent.graph_components import KNode, LabeledID
from greent.synonymizers.substance_synonymizer import synonymize
from greent.conftest import rosetta
from greent import node_types

#By and large, maintaining these tests is no longer important.  We are pre-synonymizing everything, so 
# this synonymizer should never be called.

def test_no_result(rosetta):
    """Make sure that synonymization runs"""
    #Make sure we don't throw an exception
    node = KNode('CHEBI:38253',type=node_types.CHEMICAL_SUBSTANCE)
    synonyms = synonymize(node,rosetta.core)
    assert True

def test_mesh_synonymization(rosetta):
    """Make sure that synonymization of MeSH returns the correct type (LabeledID)"""
    node = KNode('MESH:C032942', type=node_types.CHEMICAL_SUBSTANCE)
    synonyms = synonymize(node,rosetta.core)
    for s in synonyms:
        assert isinstance(s, LabeledID)

def test_chembl_synonymization(rosetta):
    """Make sure that synonymization of CHEMBL returns the correct type (LabeledID)"""
    node = KNode('CHEMBL:CHEMBL744', type=node_types.CHEMICAL_SUBSTANCE)
    synonyms = synonymize(node,rosetta.core)
    for s in synonyms:
        assert isinstance(s, LabeledID)
