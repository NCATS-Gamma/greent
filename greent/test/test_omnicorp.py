import pytest
from greent.graph_components import KNode
from greent.services.omnicorp import OmniCorp
from greent.servicecontext import ServiceContext
from greent import node_types
from greent.util import Text

@pytest.fixture(scope='module')
def omnicorpus():
    uberon = OmniCorp(ServiceContext.create_context())
    return uberon

"""These tests look at the omnicorp triple store.   This isn't used directly by interfaces any more
so it makes sense to move these elsewhere at some point."""

def test_name(omnicorpus):
    """Check conversion from CURIE to IRI"""
    cn ='CL:0000097'
    node = KNode(cn, type=node_types.CELL)
    oboid = omnicorpus.get_omni_identifier( node )
    assert oboid == 'http://purl.obolibrary.org/obo/CL_0000097'

def test_imatinib_asthma(omnicorpus):
    """Check omnicorp for papers in which imatinib and asthma both appear"""
    drug_node = KNode('CHEBI:45783', type=node_types.CHEMICAL_SUBSTANCE)
    disease_node = KNode('MONDO:0004979', type=node_types.DISEASE)
    pmids = omnicorpus.get_shared_pmids( drug_node, disease_node )
    assert len(pmids) > 0
    assert 'https://www.ncbi.nlm.nih.gov/pubmed/15374841' in pmids

def test_two_disease(omnicorpus):
    """Check omnicorp for papers in which schizophrenia and ophthalmoplegia both appear"""
    disease1 = KNode('MONDO:0005090', type=node_types.DISEASE) #schizophrenia
    disease2 = KNode('MONDO:0003425', type=node_types.DISEASE) #ophthalmoplegia
    pmids = omnicorpus.get_shared_pmids( disease1, disease2 )
    assert len(pmids) > 0

def test_list(omnicorpus):
    """Check omnicorp query to get PMIDs that contain a set of terms, not just a pair"""
    node = KNode('CL:0000097', type=node_types.CELL)
    disease_node = KNode('MONDO:0004979', type=node_types.DISEASE)
    drug_node = KNode('CHEBI:45783', type=node_types.CHEMICAL_SUBSTANCE)
    nodes = [ node, disease_node, drug_node ]
    results = omnicorpus.get_all_shared_pmids( nodes )
    assert len(results) == 3
    ids = set()
    for n1,n2 in results:
        ids.add(n1.id)
        ids.add(n2.id)
        assert len(results[(n1,n2)]) > 0
    assert len(ids) == 3
    assert 'CL:0000097' in ids
    assert 'MONDO:0004979' in ids
    assert 'CHEBI:45783' in ids

def test_list_returns_zero(omnicorpus):
    """Find a pair that returns no PMIDs"""
    disease_node = KNode('UBERON:0013694', type=node_types.ANATOMICAL_ENTITY)
    go_node = KNode('GO:0045892', type=node_types.BIOLOGICAL_PROCESS)
    nodes = [ disease_node, go_node]
    results = omnicorpus.get_all_shared_pmids( nodes )
    assert len(results) == 1
    assert len(list(results.values())[0]) == 0

def test_list_with_bad_curie(omnicorpus):
    """If we pass a curie with an unknown prefix, it is ignored"""
    node = KNode('CL:0000097', type=node_types.CELL)
    disease_node = KNode('MONDO:0004979', type=node_types.DISEASE)
    drug_node = KNode('CHEBI:45783', type=node_types.CHEMICAL_SUBSTANCE)
    stinker = KNode('FAKEO:102830', type=node_types.CHEMICAL_SUBSTANCE)
    nodes = [ node, disease_node, drug_node , stinker]
    results = omnicorpus.get_all_shared_pmids( nodes )
    assert len(results) == 6