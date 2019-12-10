import pytest
from greent.graph_components import KNode
from greent import node_types
from greent.export_type_graph import ExportGraph
from greent.conftest import rosetta

"""ExportGraph manages a subset of biolink types that are applied to nodes when they are exported"""

@pytest.fixture()
def eg(rosetta):
    return ExportGraph(rosetta)

def test_read_graph(eg):
    """Test the basic shape of the graph - there are super and subclass maps.
    named_thing has children so it is a key in subs, but it has no parents so 
    it is not a key in supers"""
    assert 'named_thing' in eg.subs
    assert 'named_thing' not in eg.supers
    assert len( eg.supers ) > 1
    assert len( eg.subs ) > 1

def test_superclasses_simplest(eg):
    """The only superclass of GENE_FAMILY is NAMED_THING"""
    sups = set()
    eg.get_superclasses(node_types.GENE_FAMILY,sups)
    assert len(sups) == 1
    assert node_types.NAMED_THING in sups

def test_superclasses_deep(eg):
    """GENETIC_CONDITION has 3 superclasses: NAMED_THING (ROOT), DISEASE_OR_PHENOTYPIC_FEATURE, and DISEASE"""
    sups = set()
    eg.get_superclasses(node_types.GENETIC_CONDITION,sups)
    assert len(sups) == 3
    assert node_types.NAMED_THING in sups
    assert node_types.DISEASE in sups
    assert node_types.DISEASE_OR_PHENOTYPIC_FEATURE in sups

def test_multiple_parents(eg):
    """GENE_PRODUCT has GENE_OR_GENE_PRODUCT and NAMED_THING, but we have also added a superclass relation to CHEMIDAL SUBSTANCE"""
    sups = set()
    eg.get_superclasses(node_types.GENE_PRODUCT,sups)
    assert len(sups) == 3
    assert node_types.NAMED_THING in sups
    assert node_types.CHEMICAL_SUBSTANCE in sups
    assert node_types.GENE_OR_GENE_PRODUCT in sups

#get_leaf_node takes a curie and finds the most subclassed type that can be applied.

def test_subclass_gene_to_gene(rosetta,eg):
    """HGNC:18729 starting at gene is a gene"""
    node = KNode('HGNC:18729', type=node_types.GENE)
    rosetta.synonymizer.synonymize(node)
    assert eg.get_leaf_type(node,node_types.GENE)[0] == node_types.GENE

def test_subclass_nt_to_gene(rosetta,eg):
    """HGNC:18729 starting at named thing is a gene"""
    node = KNode('HGNC:18729', type=node_types.NAMED_THING)
    rosetta.synonymizer.synonymize(node)
    assert eg.get_leaf_type(node,node_types.NAMED_THING)[0] == node_types.GENE

def test_subclass_nt_to_cell(rosetta,eg):
    """CL:0000556starting at named thing is a cell"""
    node = KNode('CL:0000556', type=node_types.NAMED_THING)
    #synonymizing named things gets funny, because it's hard to choose a favorite prefix
    #rosetta.synonymizer.synonymize(node)
    assert eg.get_leaf_type(node,node_types.NAMED_THING)[0] == node_types.CELL

def test_subclass_nt_to_gene_family(rosetta,eg):
    """named_thing -> Gene family"""
    node = KNode('HGNC.FAMILY:1234', type=node_types.NAMED_THING)
    rosetta.synonymizer.synonymize(node)
    assert eg.get_leaf_type(node,node_types.NAMED_THING)[0] == node_types.GENE_FAMILY

def test_subclass_nt_to_anatomical_entity(rosetta,eg):
    """named_thing -> Anatomical Entity"""
    node = KNode('UBERON:0035368', type=node_types.NAMED_THING)
    rosetta.synonymizer.synonymize(node)
    assert eg.get_leaf_type(node,node_types.NAMED_THING)[0] == node_types.ANATOMICAL_ENTITY

def test_subclass_nt_to_cellular_component(rosetta,eg):
    """named_thing -> Cellular Component"""
    node = KNode('GO:0005634', type=node_types.NAMED_THING)
    rosetta.synonymizer.synonymize(node)
    assert eg.get_leaf_type(node,node_types.NAMED_THING)[0] == node_types.CELLULAR_COMPONENT

def test_subclass_nt_to_disease(rosetta,eg):
    """named_thing -> Disease"""
    node = KNode('MONDO:0005737', type=node_types.NAMED_THING)
    rosetta.synonymizer.synonymize(node)
    assert eg.get_leaf_type(node,node_types.NAMED_THING)[0] == node_types.DISEASE

def test_subclass_nt_to_phenotypic_feature_and_disease(rosetta,eg):
    """named_thing -> (Disease,Phenotype) """
    node = KNode('HP:0002019', type=node_types.NAMED_THING)
    rosetta.synonymizer.synonymize(node)
    ltypes = eg.get_leaf_type(node,node_types.NAMED_THING)
    assert node_types.PHENOTYPIC_FEATURE in ltypes
    assert node_types.DISEASE in ltypes

def test_subclass_nt_to_phenotypic_feature(rosetta,eg):
    """named_thing -> Phenotype """
    node = KNode('HP:0001874', type=node_types.NAMED_THING)
    rosetta.synonymizer.synonymize(node)
    assert eg.get_leaf_type(node,node_types.NAMED_THING)[0]== node_types.PHENOTYPIC_FEATURE

def test_subclass_nt_to_genetic_condition(rosetta,eg):
    """named_thing -> Genetic Condition """
    node = KNode('MONDO:0019501', type=node_types.NAMED_THING)
    rosetta.synonymizer.synonymize(node)
    assert eg.get_leaf_type(node,node_types.NAMED_THING)[0] == node_types.GENETIC_CONDITION

def test_subclass_nt_to_chemical(rosetta,eg):
    """named_thing -> Chemical Substance"""
    node = KNode('CHEBI:18237', type=node_types.NAMED_THING)
    rosetta.synonymizer.synonymize(node)
    assert eg.get_leaf_type(node,node_types.NAMED_THING)[0] == node_types.CHEMICAL_SUBSTANCE

#this test relies on a filled synonym cache.  It's currently failing against prod, but passes against dev
def test_subclass_nt_to_gene_product_1(rosetta,eg):
    """named_thing -> (Chemical Substance, Gene Product)"""
    node = KNode('CHEBI:81571', type=node_types.NAMED_THING) #leptin
    rosetta.synonymizer.synonymize(node)
    print( node.synonyms )
    ltypes = eg.get_leaf_type(node,node_types.NAMED_THING)
    assert node_types.GENE_PRODUCT in ltypes
    assert node_types.CHEMICAL_SUBSTANCE in ltypes

def test_subclass_nt_to_gene_product_2(rosetta,eg):
    """named_thing -> gene"""
    #This one is weird.  We're not too sure whether uniprotkb is a gene or a gene product
    #ATM, we're ont he side of GENE
    node = KNode('UniProtKB:P31946', type=node_types.NAMED_THING)
    rosetta.synonymizer.synonymize(node)
    assert eg.get_leaf_type(node,node_types.NAMED_THING)[0] == node_types.GENE

def test_subclass_nt_to_biological_process(rosetta,eg):
    """named_thing -> biological process"""
    node = KNode('GO:0006915', type=node_types.NAMED_THING)
    rosetta.synonymizer.synonymize(node)
    assert eg.get_leaf_type(node,node_types.NAMED_THING)[0] == node_types.BIOLOGICAL_PROCESS

def test_subclass_nt_to_molecular_activity(rosetta,eg):
    """named_thing -> molecular activity"""
    node = KNode('GO:0030545', type=node_types.NAMED_THING)
    rosetta.synonymizer.synonymize(node)
    assert eg.get_leaf_type(node,node_types.NAMED_THING)[0] == node_types.MOLECULAR_ACTIVITY

