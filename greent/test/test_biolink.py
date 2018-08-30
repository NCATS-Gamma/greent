import pytest
from greent.graph_components import KNode
#from greent.services.biolink import Biolink
#from greent.ontologies.mondo import Mondo
#from greent.servicecontext import ServiceContext
from greent import node_types
from greent.util import Text
from greent.conftest import rosetta


@pytest.fixture()
def biolink(rosetta):
    #biolink = Biolink(ServiceContext.create_context())
    biolink = rosetta.core.biolink
    return biolink

@pytest.fixture()
def mondo(rosetta):
    #checker = Mondo(ServiceContext.create_context())
    checker = rosetta.core.checker
    return checker

def test_bad_gene_to_process(biolink):
    BAD_protein = KNode('UniProtKB:XXXXXX', type=node_types.GENE)
    results = biolink.gene_get_process_or_function(BAD_protein)
    assert len(results) == 0


def test_gene_to_disease(biolink):
    """What do we get back for HBB"""
    relations = biolink.gene_get_disease(KNode('HGNC:4827', type=node_types.GENE))
    assert len(relations) > 20 and len(relations) < 40
    identifiers = [node.id for r,node in relations]
    #everthing should be MONDO ids
    for ident in identifiers:
        assert Text.get_curie(ident) == 'MONDO'
    #Sickle cell should be in there.
    assert 'MONDO:0011382' in identifiers
    predicates = [ relation.standard_predicate for relation,n in relations ] 
    pids = set( [p.identifier for p in predicates] )
    plabels = set( [p.label for p in predicates] )
    assert 'RO:0002607' in pids
    assert 'gene_associated_with_condition' in plabels


def test_gene_to_process(biolink):
    KIT_protein = KNode('HGNC:6432', type=node_types.GENE)
    results = biolink.gene_get_process_or_function(KIT_protein)
    #When this test fails, it will indicate that monarch fixed the mapping in the gene/function endpoint
    #At that point, change to assert len(results) > 0, and take out all the UniProt jazz in the client.
    assert len(results) == 0
    for ke, kn in results:
        assert kn.type == node_types.BIOLOGICAL_PROCESS_OR_ACTIVITY
        assert Text.get_curie(kn.id) == "GO"

def test_gene_to_process2(biolink):
    KIT_protein = KNode('UniProtKB:Q14994', type=node_types.GENE)
    results = biolink.gene_get_process_or_function(KIT_protein)
    for ke, kn in results:
        assert kn.type == node_types.BIOLOGICAL_PROCESS_OR_ACTIVITY
        assert Text.get_curie(kn.id) == "GO"

def test_disease_to_phenotypes(biolink):
    #This tests pagination as well
    asthma = KNode('DOID:2841', type=node_types.DISEASE)
    results = biolink.disease_get_phenotype(asthma)
    assert len(results) > 100
    identifiers = [node.id for r,node in results]
    #everthing should be MONDO ids
    for ident in identifiers:
        assert Text.get_curie(ident) == 'HP'
    #acute severe asthma should be in there.
    assert 'HP:0012653' in identifiers

def test_pathways(biolink):
    gene_id = 'HGNC:5013'
    gene = KNode(gene_id, type=node_types.GENE)
    results = biolink.gene_get_pathways(gene)
    for e, k in results:
        assert k.type == node_types.PATHWAY
    e,k = results[0]
    presults = biolink.pathway_get_gene(k)
    #Just check for one result
    for pe,pk in presults:
        assert pk.type == node_types.GENE
    gene_ids = [ pk.id for pe,pk in presults ]
    assert gene_id in gene_ids
