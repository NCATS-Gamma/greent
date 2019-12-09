from greent.graph_components import KNode
from greent.synonymizers.oxo_synonymizer import synonymize
from greent.conftest import rosetta
from greent import node_types

def test_neuron(rosetta):
    node = KNode("CL:0000540", type=node_types.CELL)
    synonymize(node,rosetta.core)
    assert len(node.synonyms) >  5
    #we're no longer so pathological about trying to get meshIDs so in this case we don't get one
    meshcell = node.get_synonyms_by_prefix("MESH")
    assert len(meshcell) == 0
    #BUt we should get a FMA?
    #We used to get a UMLS, but OXO isn't giving us that for some reason...
    umlscell = node.get_synonyms_by_prefix("FMA")
    mid = list(umlscell)[0]
    assert mid == 'FMA:54527' \

def test_phenotype(rosetta):
    """Check that we're getting back results from meddra.  Because we're limiting to distance=1 from oxo, we're
    only getting back UMLS terms for this phenotype.  If we allowed bigger distance (2) we would also get HP etc."""
    node = KNode("MEDDRA:10014408", type=node_types.PHENOTYPIC_FEATURE)
    synonymize(node,rosetta.core)
    assert len(node.synonyms) > 5
    hpsyns = node.get_synonyms_by_prefix("UMLS")
    assert len(hpsyns) > 0
    print(hpsyns)

def test_names(rosetta):
    node = KNode('HP:0002527', type=node_types.PHENOTYPIC_FEATURE, name='Falls')
    synonymize(node,rosetta.core)
    print( node.synonyms )
    msyns = node.get_labeled_ids_by_prefix("UMLS")
    assert len(msyns) == 1
    ms = msyns.pop()
    assert ms.identifier == 'UMLS:C0085639'
    assert ms.label == 'Falls'

