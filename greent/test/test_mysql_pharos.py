import pytest
from greent.graph_components import KNode, LabeledID
from greent import node_types
from greent.util import Text
from greent.conftest import rosetta

@pytest.fixture()
def pharos(rosetta):
    pharos = rosetta.core.pharos
    return pharos

def test_drug_get_gene(pharos):
    """Check pharos drug->Gene.  Celecoxib->PTGS2"""
    #pharos should find chembl in the synonyms
    node = KNode('DB:FakeyName', type=node_types.CHEMICAL_SUBSTANCE)
    node.add_synonyms([LabeledID(identifier='CHEMBL:CHEMBL118', label='blahbalh')])
    results = pharos.drug_get_gene(node)
    #we get results
    assert len(results) > 0
    #They are gene nodes:
    ntypes = set([n.type for e,n in results])
    assert node_types.GENE in ntypes
    assert len(ntypes) == 1
    #All of the ids should be HGNC
    identifiers = [n.id for e,n in results]
    prefixes = set([ Text.get_curie(i) for i in identifiers])
    assert 'HGNC' in prefixes
    assert len(prefixes) == 1
    #PTGS2 (COX2) (HGNC:9605) should be in there
    assert 'HGNC:9605' in identifiers

def test_drug_get_gene_other_table(pharos):
    """The mysql version of pharos has to check a couple of tables.  This test access the other
    table of relevance by looking for this unnamed chemical to MAPK1"""
    #pharos should find chembl in the synonyms
    node = KNode('DB:FakeyName', type=node_types.CHEMICAL_SUBSTANCE)
    node.add_synonyms([LabeledID(identifier='CHEMBL:CHEMBL3658657', label='blahbalh')])
    results = pharos.drug_get_gene(node)
    #we get results
    assert len(results) > 0
    #They are gene nodes:
    ntypes = set([n.type for e,n in results])
    assert node_types.GENE in ntypes
    assert len(ntypes) == 1
    #All of the ids should be HGNC
    identifiers = [n.id for e,n in results]
    prefixes = set([ Text.get_curie(i) for i in identifiers])
    assert 'HGNC' in prefixes
    assert len(prefixes) == 1
    assert 'HGNC:6871' in identifiers


def test_gene_get_drug_long(pharos,rosetta):
    """go gene->chemical from MAPK1"""
    gene_node = KNode('HGNC:6871', type=node_types.GENE)
    rosetta.synonymizer.synonymize(gene_node)
    output = pharos.gene_get_drug(gene_node)
    identifiers = [ output_i[1].id for output_i in output ]
    assert len(identifiers) > 50
    assert 'CHEMBL:CHEMBL3658657'in identifiers

def test_gene_get_drug(pharos,rosetta):
    """Go gene->drug, PTSG2->Celecoxib"""
    gene_node = KNode('HGNC:9605', type=node_types.GENE)
    rosetta.synonymizer.synonymize(gene_node)
    print(gene_node.synonyms)
    
    output = pharos.gene_get_drug(gene_node)
    identifiers = [ output_i[1].id for output_i in output ]
    assert 'CHEMBL:CHEMBL118'in identifiers

def test_disease_get_gene(pharos,rosetta):
    """Check genes from disease, Ebola->NPC1"""
    disease_node = KNode('DOID:4325', type=node_types.DISEASE, name="ebola")
    output = pharos.disease_get_gene(disease_node)
    identifiers = [ output_i[1].id for output_i in output ]
    assert 'HGNC:7897' in identifiers

def test_disease_gene_mondo(pharos,rosetta):
    """Check disease->gene, starting from a mondo instead of pharos' preferred (DOID). Starting with Lung Cancer"""
    d_node = KNode('MONDO:0008903', type=node_types.DISEASE)
    rosetta.synonymizer.synonymize(d_node)
    output = pharos.disease_get_gene(d_node)
    identifiers = [ output_i[1].id for output_i in output ]
    assert 'HGNC:9884' in identifiers #RB1
    assert 'HGNC:6407' in identifiers #KRAS

def test_gene_get_disease(pharos):
    """Gene->Disease starting with ZNF214"""
    gnode = KNode('HGNC:13006',type=node_types.GENE)
    results = pharos.gene_get_disease(gnode)
    identifiers = [(r[1].id,r[1].name) for r in results]
    #This used to be 9 but lowered when we excluded Expression data.
    assert len(identifiers)==3
    assert ('DOID:305','Carcinoma') in identifiers
    assert ('DOID:11383','Cryptorchidism') in identifiers

