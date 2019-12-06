import pytest
from greent.graph_components import KNode
from greent import node_types
from greent.export_type_graph import ExportGraph
from greent.conftest import rosetta


@pytest.fixture()
def eg(rosetta):
    return ExportGraph(rosetta)

def test_read_graph(eg):
    #Named thing has children, but not a parent, so
    assert 'named_thing' in eg.subs
    assert 'named_thing' not in eg.supers
    assert len( eg.supers ) > 1
    assert len( eg.subs ) > 1

def test_superclasses_simplest(eg):
    sups = set()
    eg.get_superclasses(node_types.GENE_FAMILY,sups)
    assert len(sups) == 1
    assert node_types.NAMED_THING in sups

def test_superclasses_deep(eg):
    sups = set()
    eg.get_superclasses(node_types.GENETIC_CONDITION,sups)
    assert len(sups) == 3
    assert node_types.NAMED_THING in sups
    assert node_types.DISEASE in sups
    assert node_types.DISEASE_OR_PHENOTYPIC_FEATURE in sups

def test_multiple_parents(eg):
    sups = set()
    eg.get_superclasses(node_types.GENE_PRODUCT,sups)
    assert len(sups) == 3
    assert node_types.NAMED_THING in sups
    assert node_types.CHEMICAL_SUBSTANCE in sups
    assert node_types.GENE_OR_GENE_PRODUCT in sups

def test_subclass_gene_to_gene(rosetta,eg):
    node = KNode('HGNC:18729', type=node_types.GENE)
    rosetta.synonymizer.synonymize(node)
    assert eg.get_leaf_type(node,node_types.GENE)[0] == node_types.GENE

def test_subclass_nt_to_gene(rosetta,eg):
    node = KNode('HGNC:18729', type=node_types.NAMED_THING)
    rosetta.synonymizer.synonymize(node)
    assert eg.get_leaf_type(node,node_types.NAMED_THING)[0] == node_types.GENE

def test_subclass_nt_to_cell(rosetta,eg):
    node = KNode('CL:0000556', type=node_types.NAMED_THING)
    #synonymizing named things gets funny, because it's hard to choose a favorite prefix
    #rosetta.synonymizer.synonymize(node)
    assert eg.get_leaf_type(node,node_types.NAMED_THING)[0] == node_types.CELL

def test_subclass_nt_to_gene_family(rosetta,eg):
    node = KNode('HGNC.FAMILY:1234', type=node_types.NAMED_THING)
    rosetta.synonymizer.synonymize(node)
    assert eg.get_leaf_type(node,node_types.NAMED_THING)[0] == node_types.GENE_FAMILY

def test_subclass_nt_to_anatomical_entity(rosetta,eg):
    node = KNode('UBERON:0035368', type=node_types.NAMED_THING)
    rosetta.synonymizer.synonymize(node)
    assert eg.get_leaf_type(node,node_types.NAMED_THING)[0] == node_types.ANATOMICAL_ENTITY

def test_subclass_nt_to_cellular_component(rosetta,eg):
    node = KNode('GO:0005634', type=node_types.NAMED_THING)
    rosetta.synonymizer.synonymize(node)
    assert eg.get_leaf_type(node,node_types.NAMED_THING)[0] == node_types.CELLULAR_COMPONENT

def test_subclass_nt_to_disease(rosetta,eg):
    node = KNode('MONDO:0005737', type=node_types.NAMED_THING)
    rosetta.synonymizer.synonymize(node)
    assert eg.get_leaf_type(node,node_types.NAMED_THING)[0] == node_types.DISEASE

def test_subclass_nt_to_phenotypic_feature_and_disease(rosetta,eg):
    node = KNode('HP:0002019', type=node_types.NAMED_THING)
    rosetta.synonymizer.synonymize(node)
    ltypes = eg.get_leaf_type(node,node_types.NAMED_THING)
    assert node_types.PHENOTYPIC_FEATURE in ltypes
    assert node_types.DISEASE in ltypes

def test_subclass_nt_to_phenotypic_feature(rosetta,eg):
    node = KNode('HP:0001874', type=node_types.NAMED_THING)
    rosetta.synonymizer.synonymize(node)
    assert eg.get_leaf_type(node,node_types.NAMED_THING)[0]== node_types.PHENOTYPIC_FEATURE

def test_subclass_nt_to_genetic_condition(rosetta,eg):
    node = KNode('MONDO:0019501', type=node_types.NAMED_THING)
    rosetta.synonymizer.synonymize(node)
    assert eg.get_leaf_type(node,node_types.NAMED_THING)[0] == node_types.GENETIC_CONDITION

def test_subclass_nt_to_chemical(rosetta,eg):
    node = KNode('CHEBI:18237', type=node_types.NAMED_THING)
    rosetta.synonymizer.synonymize(node)
    assert eg.get_leaf_type(node,node_types.NAMED_THING)[0] == node_types.CHEMICAL_SUBSTANCE

#this test relies on a filled synonym cache
def test_subclass_nt_to_gene_product_1(rosetta,eg):
    node = KNode('CHEBI:81571', type=node_types.NAMED_THING) #leptin
    rosetta.synonymizer.synonymize(node)
    print( node.synonyms )
    assert eg.get_leaf_type(node,node_types.NAMED_THING)[0] == node_types.GENE_PRODUCT

def test_subclass_nt_to_gene_product_2(rosetta,eg):
    #This one is weird.  We're not too sure whether uniprotkb is a gene or a gene product
    #ATM, we're ont he side of GENE
    node = KNode('UniProtKB:P31946', type=node_types.NAMED_THING)
    rosetta.synonymizer.synonymize(node)
    assert eg.get_leaf_type(node,node_types.NAMED_THING)[0] == node_types.GENE

def test_subclass_nt_to_biological_process(rosetta,eg):
    node = KNode('GO:0006915', type=node_types.NAMED_THING)
    rosetta.synonymizer.synonymize(node)
    assert eg.get_leaf_type(node,node_types.NAMED_THING)[0] == node_types.BIOLOGICAL_PROCESS

def test_subclass_nt_to_molecular_activity(rosetta,eg):
    node = KNode('GO:0030545', type=node_types.NAMED_THING)
    rosetta.synonymizer.synonymize(node)
    assert eg.get_leaf_type(node,node_types.NAMED_THING)[0] == node_types.MOLECULAR_ACTIVITY

