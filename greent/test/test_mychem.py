import pytest
from greent.graph_components import KNode,LabeledID
from greent import node_types
from greent.util import Text
from greent.conftest import rosetta
from greent.synonymizers.disease_synonymizer import synonymize


@pytest.fixture()
def mychem(rosetta):
    mychem = rosetta.core.mychem
    return mychem

def test_drugcentral(mychem):
    """Check that Celecoxib treates Rheumatoid Arthritis (3873) and is contraindicated for Cardiovascular Disease (7222)"""
    node = KNode('CHEMBL:CHEMBL118', type=node_types.CHEMICAL_SUBSTANCE, name='Celecoxib') #Celecoxib
    results = mychem.get_drugcentral(node)
    found1 = False
    found2 = False
    for e,n in results:
        if n.id == 'UMLS:C0007222':
            found1 = True
            assert e.original_predicate.label == 'contraindication'
        if n.id == 'UMLS:C0003873':
            found2 = True
            assert e.original_predicate.label == 'treats'
        assert e.provided_by == 'mychem.get_drugcentral'
    assert found1
    assert found2

def test_glyburide(rosetta,mychem):
    """Test that glyburide treats diabetes, but is contraindicated for communicable diseases"""
    node = KNode('CHEBI:5441', type=node_types.CHEMICAL_SUBSTANCE, name='glyburide')
    rosetta.synonymizer.synonymize(node)
    results = mychem.get_drugcentral(node)
    found1 = False
    found2 = False
    for e,n in results:
        print(e.original_predicate.label, n)
        if n.id == 'UMLS:C0009450': #communicable diseases
            found1 = True
            assert e.original_predicate.label == 'contraindication'
        if n.id == 'UMLS:C0011860': #diabetes
            found2 = True
            assert e.original_predicate.label == 'treats'
        assert e.provided_by == 'mychem.get_drugcentral'
    assert found1
    assert found2

def test_glyburide_aeolus(rosetta,mychem):
    """check adverse events of glyburide include weight increase, nausea, vomiting"""
    node = KNode('CHEBI:5441', type=node_types.CHEMICAL_SUBSTANCE, name='glyburide')
    rosetta.synonymizer.synonymize(node)
    results = mychem.get_adverse_events(node)
    r = [(e.original_predicate.label, n.name) for e,n in results]
    assert ('causes_or_contributes_to', 'Weight increased') in r
    assert ('causes_or_contributes_to', 'Nausea') in r
    assert ('causes_or_contributes_to', 'Vomiting') in r

def test_drug_adverse_events(mychem):
    """Smoke check for adverse events; Calling with escitalopram produces results"""
    node = KNode('CHEMBL:CHEMBL1508', type=node_types.CHEMICAL_SUBSTANCE) #Escitalopram
    results = mychem.get_adverse_events(node)
    assert len(results) > 0

def test_atorvastatin(mychem):
    """Smoke check for adverse events; Calling with atorvastatin produces results"""
    node = KNode('CHEMBL:CHEMBL1487', type=node_types.CHEMICAL_SUBSTANCE) #Atorvastatin
    results = mychem.get_adverse_events(node)
    assert len(results) > 0


#This test is accurate, but pheno filter is slow, so it doesn't make a good test
def x_test_with_pheno_filter(rosetta):
    """This will usually get called with a phenotype filter"""
    fname='caster.output_filter(mychem~get_adverse_events,phenotypic_feature,typecheck~is_phenotypic_feature)'
    func = rosetta.get_ops(fname)
    assert func is not None
    #Escitalopram
    results = func(KNode('CHEMBL:CHEMBL1508', type=node_types.CHEMICAL_SUBSTANCE))
    assert len(results) > 0

def test_drug_gene(mychem):
    """Check Alfentanyl -> ORPM1"""
    node = KNode('DRUGBANK:DB00802', type=node_types.CHEMICAL_SUBSTANCE) # Alfentanyl
    results = mychem.get_gene_by_drug(node)
    ids = [n.id for e,n in results]
    assert 'UNIPROTKB:P35372' in ids