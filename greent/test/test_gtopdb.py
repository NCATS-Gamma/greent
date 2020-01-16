import pytest
from greent.graph_components import KNode
from greent import node_types
from greent.graph_components import LabeledID
from greent.conftest import rosetta


@pytest.fixture()
def gtopdb(rosetta):
    g = rosetta.core.gtopdb
    return g

def test_vasopressin_precursor(gtopdb):
    """Which gene produces the chemical product Vasopressin?"""
    input_node = KNode("GTOPDB:2168", type=node_types.CHEMICAL_SUBSTANCE, name="Vasopressin")
    results = gtopdb.chem_to_precursor(input_node)
    assert len(results) == 1
    for edge,node in results:
        assert node.type == node_types.GENE
        assert node.id == 'HGNC:894'

def test_vasopressin_genes(gtopdb):
    """Vasopressin is the ligand of which gene?"""
    input_node = KNode("GTOPDB:2168", type=node_types.CHEMICAL_SUBSTANCE, name="Vasopressin")
    results = gtopdb.ligand_to_gene(input_node)
    assert len(results) == 4
    for edge,node in results:
        assert node.type == node_types.GENE
    node_ids = [n.id for e,n in results]
    #Vasopressin receptors V1A, V1B, V2, OXTR
    assert 'IUPHAR:368' in node_ids
    assert 'IUPHAR:366' in node_ids
    assert 'IUPHAR:367' in node_ids
    assert 'IUPHAR:369' in node_ids

