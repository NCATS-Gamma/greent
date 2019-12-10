from greent.graph_components import KNode
from greent.synonymizers.hgnc_synonymizer import synonymize
from greent.conftest import rosetta
from greent import node_types
from greent.synonymizers import hgnc_synonymizer

def test_uniprot(rosetta):
    """Do we correctly synonymize if all we have is a UniProtKB identifier?"""
    node = KNode('UniProtKB:O75381', type=node_types.GENE)
    rosetta.synonymizer.synonymize(node)
    hgnc = node.get_synonyms_by_prefix('HGNC')
    assert len(hgnc) == 1
    assert hgnc.pop() == 'HGNC:8856'
    assert node.id == 'HGNC:8856'

def test_trembl(rosetta):
    """Do we correctly synonymize if all we have is a Trembl?"""
    node = KNode('UniProtKB:A0A024QZH5', type=node_types.GENE)
    rosetta.synonymizer.synonymize(node)
    hgnc = node.get_synonyms_by_prefix('HGNC')
    assert len(hgnc) == 1

def test_good_uniprot(rosetta):
    """Do we correctly synonymize if all we have is a UniProtKB identifier?"""
    node = KNode('UniProtKB:P01160', type=node_types.GENE)
    rosetta.synonymizer.synonymize(node)
    hgnc = node.get_synonyms_by_prefix('HGNC')
    assert len(hgnc) == 1
    assert hgnc.pop() == 'HGNC:7939'
    assert node.id == 'HGNC:7939'

def test_good_uniprot_2(rosetta):
    """Do we correctly synonymize if all we have is a UniProtKB identifier?"""
    node = KNode('UniProtKB:P14416', type=node_types.GENE, name='')
    rosetta.synonymizer.synonymize(node)
    hgnc = node.get_synonyms_by_prefix('HGNC')
    assert len(hgnc) == 1
    assert hgnc.pop() == 'HGNC:3023'
    assert node.id == 'HGNC:3023'

def test_gene_synonymizer(rosetta):
    node = KNode('NCBIGENE:57016', type=node_types.GENE)
    results = hgnc_synonymizer.synonymize(node,rosetta.core)
    assert len(results) > 0
