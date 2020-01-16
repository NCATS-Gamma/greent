import pytest
from greent.graph_components import KNode
from greent import node_types
from greent.graph_components import LabeledID
from greent.conftest import rosetta


@pytest.fixture()
def ctd(rosetta):
    ctd = rosetta.core.ctd
    return ctd

def test_expanded_drug_to_gene(ctd):
    """Find genes associated with Diazinon.  Make sure that all predicates are properly transformed, and that at
    least ACHE (HGNC:108) is returned"""
    input_node = KNode("MESH:D003976", type=node_types.CHEMICAL_SUBSTANCE, name="Diazinon")
    results = ctd.drug_to_gene_expanded(input_node)
    genes = [node.id for edge,node in results]
    assert 'NCBIGENE:43' in genes
    for edge,node in results:
        assert node.type == node_types.GENE
        assert edge.standard_predicate.identifier != 'GAMMA:0'

def test_expanded_drug_to_gene_too_many(ctd):
    """check that we can handle a large number of chem->gene results, that we transform
    all predicates correctly, and that we're returning a large number of different predicates"""
    input_node = KNode("MESH:D001335", type=node_types.CHEMICAL_SUBSTANCE, name="question")
    results = ctd.drug_to_gene_expanded(input_node)
    assert len(results) > 200
    preds = set()
    for edge,node in results:
        assert node.type == node_types.GENE
        assert edge.standard_predicate.identifier != 'GAMMA:0'
        preds.add(edge.standard_predicate.identifier)
    assert len(preds) > 15

def test_expanded_drug_to_gene_glucose(ctd,rosetta):
    """Check that given a CHEBI, we can synonymize to mesh and the ctd client will
    find the right identfier, and return genes, along with properly mapped predictes.
    Also check that the gene INS is returned"""
    input_node = KNode("CHEBI:17234", type=node_types.CHEMICAL_SUBSTANCE, name="Glucose")
    rosetta.synonymizer.synonymize(input_node)
    results = ctd.drug_to_gene_expanded(input_node)
    assert len(results) > 0
    for edge,node in results:
        assert node.type == node_types.GENE
        assert edge.standard_predicate.identifier != 'GAMMA:0'
    node_ids = [node.id for e,node in results]
    assert 'NCBIGENE:3630' in node_ids

def test_expanded_gene_to_drug_fails(ctd,rosetta):
    """This gene has nominal results, but the publication support is insufficient.
    Check that they are being filtered out (i.e. that no results are returned"""
    input_node = KNode("HGNC:1305", type=node_types.GENE, name="C6ORF21")
    rosetta.synonymizer.synonymize(input_node)
    results = ctd.gene_to_drug_expanded(input_node)
    assert len(results) == 0


def test_disease_to_chemical(rosetta,ctd):
    """Check that disease->chemical can take a synonymized MONDO, and return many
    chemicals, along with correctly mapped edge predicates"""
    input_node = KNode("MONDO:0004979", type=node_types.DISEASE, name='Asthma')
    rosetta.synonymizer.synonymize(input_node)
    results = ctd.disease_to_chemical(input_node)
    #Now, we're not returning the inferred ones.
    assert len(results) > 100
    for edge, node in results:
        assert node.type == node_types.CHEMICAL_SUBSTANCE
        assert edge.standard_predicate.identifier != 'GAMMA:0'

def test_gene_to_drug_and_back(ctd):
    """Check that we get the same results whether we go drug->gene or gene->drug"""
    input_node = KNode('MESH:D003976', type=node_types.GENE, name='Diazinon')
    results = ctd.drug_to_gene_expanded(input_node)
    results = list(filter(lambda en: en[1].id == 'NCBIGENE:5243', results))
    for edge, node in results:
        assert node.type == node_types.GENE
        assert edge.standard_predicate.identifier != 'GAMMA:0'
    dgedges = set([e.original_predicate.label for e, n in results])
    input_node_2 = KNode('NCBIGENE:5243', type=node_types.GENE, name='ABCB1')
    results = ctd.gene_to_drug_expanded(input_node_2)
    for edge, node in results:
        assert node.type == node_types.CHEMICAL_SUBSTANCE
        assert edge.standard_predicate.identifier != 'GAMMA:0'
    results = list(filter(lambda en: en[1].id == 'MESH:D003976', results))
    gdedges = set([e.original_predicate.label for e, n in results])
    assert dgedges == gdedges


def test_drugname_to_mesh(ctd):
    """Check that we can look up drug names to get mesh ids"""
    nodes = ctd.drugname_string_to_drug("Celecoxib")
    assert len(nodes) == 1
    assert nodes[0].type == node_types.CHEMICAL_SUBSTANCE
    assert nodes[0].id == 'MESH:D000068579'

def test_drugname_to_mesh_wacky_caps(ctd):
    """Check that we can look up drug names to get mesh ids and that this is case insensitive"""
    nodes = ctd.drugname_string_to_drug("cElEcOxIb")
    assert len(nodes) == 1
    assert nodes[0].type == node_types.CHEMICAL_SUBSTANCE
    assert nodes[0].id == 'MESH:D000068579'


def test_drugname_to_mesh_synonym(ctd):
    """Check that we can look up drug names to get mesh ids even if we use a mesh lexical synonym"""
    nodes = ctd.drugname_string_to_drug('2,5-dimethyl-celecoxib')
    assert len(nodes) == 1
    assert nodes[0].type == node_types.CHEMICAL_SUBSTANCE
    assert nodes[0].id == 'MESH:C506698'



def test_drug_to_gene_simple(ctd):
    """Check that we will return COX2 as related to a COX2 inhibitor"""
    input_node = KNode("MESH:D000068579", type=node_types.CHEMICAL_SUBSTANCE)
    results = ctd.drug_to_gene_expanded(input_node)
    for edge, node in results:
        assert node.type == node_types.GENE
        assert edge.standard_predicate.identifier != 'GAMMA:0'
    result_ids = [node.id for edge, node in results]
    assert 'NCBIGENE:5743' in result_ids  # Cox2 for a cox2 inhibitor

def test_drug_to_gene_Huge(ctd):
    """Make sure that we can process a large number of results"""
    input_node = KNode("MESH:D014635", name="Valproic Acid", type=node_types.CHEMICAL_SUBSTANCE)
    results = ctd.drug_to_gene_expanded(input_node)
    #OK, this looks like a lot, but it's better than the 30000 we had before filtering.
    assert len(results) < 7000
    assert len(results) > 6000

def test_drug_to_gene_synonym(ctd):
    """Test whether drug to gene can work if mesh is an equivalent identifier, but DB is the main identifier"""
    # Even though the main identifier is drugbank, CTD should find the right synonym in there somewhere.
    input_node = KNode("DB:FakeID", type=node_types.CHEMICAL_SUBSTANCE)
    input_node.add_synonyms(set([LabeledID(identifier="MESH:D000068579", label="blah")]))
    results = ctd.drug_to_gene_expanded(input_node)
    for edge, node in results:
        assert node.type == node_types.GENE
        assert edge.standard_predicate.identifier != 'GAMMA:0'
    result_ids = [node.id for edge, node in results]
    assert 'NCBIGENE:5743' in result_ids  # Cox2 for a cox2 inhibitor


def test_gene_to_drug_unique(ctd):
    """Test gene to drug.  APOC3 should be linked to pirixinic acid.  Test that each result is unique."""
    input_node = KNode("NCBIGENE:345", type=node_types.GENE)  # APOC3
    results = ctd.gene_to_drug_expanded(input_node)
    outputs = [(e.original_predicate, n.id) for e, n in results]
    total = len(outputs)
    unique = len(set(outputs))
    for edge, n in results:
        assert edge.standard_predicate.identifier != 'GAMMA:0'
    assert total == unique
    assert 'MESH:C006253' in [n.id for e,n in results]

def test_gene_to_drug_CASP3(ctd,rosetta):
    """CASP3 should be related to reveratrol"""
    input_node = KNode("HGNC:1504", type=node_types.GENE)  # CASP3
    rosetta.synonymizer.synonymize(input_node)
    results = ctd.gene_to_drug_expanded(input_node)
    #See note in test_gene_to_drug_unique
    outputs = [(e.original_predicate, n.id) for e, n in results]
    total = len(outputs)
    unique = len(set(outputs))
    found = False
    for e, n in results:
        assert e.standard_predicate.identifier != 'GAMMA:0'
        if (n.id == 'MESH:C059514'):
            found = True
    assert total == unique
    assert found

def test_gene_to_drug_ACHE(ctd):
    """Test gene->drug ACHE->Diazinon """
    input_node = KNode("NCBIGENE:43", type=node_types.GENE)  # ACHE
    results = ctd.gene_to_drug_expanded(input_node)
    #See note in test_gene_to_drug_unique
    outputs = [(e.original_predicate, n.id) for e, n in results]
    total = len(outputs)
    unique = len(set(outputs))
    for e, n in results:
        assert e.standard_predicate.identifier != 'GAMMA:0'
    assert 'MESH:D003976' in [n.id for e,n in results]
    assert total == unique


def test_gene_to_drug_synonym(ctd):
    """Test gene -> drug, where the drug has the necessary id as an equivalent
    Test PTGS2 -> Celecoxib"""
    # Even though the main identifier is drugbank, CTD should find the right synonym in there somewhere.
    input_node = KNode("DB:FakeID", type=node_types.GENE)
    input_node.add_synonyms(set(["NCBIGene:5743"]))
    results = ctd.gene_to_drug_expanded(input_node)
    for e, node in results:
        assert e.standard_predicate.identifier != 'GAMMA:0'
        assert node.type == node_types.CHEMICAL_SUBSTANCE
    result_ids = [node.id for edge, node in results]
    assert 'MESH:D000068579' in result_ids 

def test_gene_to_drug_BCL2(ctd,rosetta):
    """Test BCL2 -> Doxirubicin"""
    input_node = KNode("HGNC:990", type=node_types.GENE, name="BCL2")
    rosetta.synonymizer.synonymize(input_node)
    results = ctd.gene_to_drug_expanded(input_node)
    assert len(results) > 0
    for edge,node in results:
        assert node.type == node_types.CHEMICAL_SUBSTANCE
        assert edge.standard_predicate.identifier != 'GAMMA:0'
    result_ids = [node.id for edge, node in results]
    assert 'MESH:D004317' in result_ids 

def test_chemical_to_gene_glutathione(ctd):
    """Test chem->gene glutathione - > GSTM1"""
    input_node = KNode("MESH:D006861", type=node_types.CHEMICAL_SUBSTANCE)
    results = ctd.drug_to_gene_expanded(input_node)
    for edge, node in results:
        assert edge.standard_predicate.identifier != 'GAMMA:0'
        assert node.type == node_types.GENE
    for edge, node in results:
        if node.id == edge.target_id:
            direction = '+'
        elif node.id == edge.source_id:
            direction = '-'
        else:
            print("wat")
        print(edge.original_predicate.identifier, edge.standard_predicate.identifier, node.id, direction)
    result_ids = [node.id for edge, node in results]
    assert 'NCBIGENE:2944' in result_ids  


def test_disease_to_exposure(ctd):
    """Test the exposure API Disease -> Exposure
    Test Asthma -> DDT"""
    input_node = KNode("MESH:D001249", type=node_types.DISEASE, name='Asthma')
    results = ctd.disease_to_exposure(input_node)
    ddt = None
    for edge, node in results:
        assert node.type == node_types.CHEMICAL_SUBSTANCE
        assert edge.standard_predicate.identifier != 'GAMMA:0'
        if node.id == 'MESH:D003634':
            ddt = node
    assert len(results) > 0
    assert ddt is not None
    assert ddt.name == 'DDT'



