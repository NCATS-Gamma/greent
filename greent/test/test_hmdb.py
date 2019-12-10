import pytest
from greent.graph_components import KNode
from greent.services.hmdb_beacon import HMDB
from greent import node_types
from greent.util import Text
from greent.conftest import rosetta


@pytest.fixture()
def hmdb(rosetta):
    hmdb = rosetta.core.hmdb
    return hmdb

def test_metabolite_to_disease_with_syn(rosetta,hmdb):
    """Check that D-glucose is associted with T2D"""
    chem = KNode('CHEBI:4167', type = node_types.CHEMICAL_SUBSTANCE)
    rosetta.synonymizer.synonymize(chem)
    results = hmdb.metabolite_to_disease(chem)
    for e,n in results:
        rosetta.synonymizer.synonymize(n)
    ids = [n.id for e,n in results]
    assert "MONDO:0005148" in ids

def test_metabolite_to_enzyme_with_syn(rosetta,hmdb):
    """Check chemical->gene; is caffiene associated with PED4B"""
    chem = KNode('CHEBI:27732', type=node_types.CHEMICAL_SUBSTANCE)
    rosetta.synonymizer.synonymize(chem)
    results = hmdb.metabolite_to_enzyme(chem)
    assert len(results) > 0
    assert 'UniProtKB:Q07343'  in [n.id for e,n in results]

def test_diabetes_to_metabolite(rosetta,hmdb):
    """Disease -> metabolite.   T2D -> Uric Acid"""
    diabetes = KNode('MONDO:0005148', type=node_types.DISEASE)
    rosetta.synonymizer.synonymize(diabetes)
    print(diabetes.synonyms)
    results = hmdb.disease_to_metabolite(diabetes)
    assert len(results) > 0
    node_labels=[node.name for edge,node in results]
    assert 'Uric acid' in node_labels

def test_disease_to_metabolite(hmdb):
    """Test Asthma -> 5-HETE"""
    asthma = KNode('UMLS:C0004096', type=node_types.DISEASE)
    results = hmdb.disease_to_metabolite(asthma)
    assert len(results) > 0
    node_labels=[node.name for edge,node in results]
    assert '5-HETE' in node_labels

def test_enzyme_to_metabolite(hmdb):
    """Gene -> metabolite.   GPX7->5-HETE"""
    asthma = KNode('UniProtKB:Q96SL4', type=node_types.GENE)
    results = hmdb.enzyme_to_metabolite(asthma)
    assert len(results) > 0
    node_labels=[node.name for edge,node in results]
    assert '5-HETE' in node_labels

def _test_pathway_to_metabolite(hmdb):
    pathway = KNode('SMPDB:SMP00710', type=node_types.PATHWAY)
    results = hmdb.pathway_to_metabolite(pathway)
    assert len(results) > 0
    #make sure we got a metabolite we expect
    node_labels=[node.name for edge,node in results]
    assert '5-HETE' in node_labels
    #we're looking up by pathway, but pathway should be the object, is it?
    for edge,node in results:
        assert edge.target_id == pathway.id


def test_metabolite_to_disease(hmdb):
    """Metabolite->Disease,  5-HETE -> asthma"""
    hete = KNode('HMDB:HMDB0011134', type=node_types.CHEMICAL_SUBSTANCE)
    results = hmdb.metabolite_to_disease(hete)
    assert len(results) > 0
    node_labels=[node.name for edge,node in results]
    assert 'Asthma' in node_labels

def test_metabolite_to_enzyme(hmdb):
    """Metabolite->Gene,  5-HETE -> GPX7"""
    hete = KNode('HMDB:HMDB0011134', type=node_types.CHEMICAL_SUBSTANCE)
    results = hmdb.metabolite_to_enzyme(hete)
    assert len(results) > 0
    node_ids=[node.id for edge,node in results]
    assert 'UniProtKB:Q96SL4' in node_ids

def _test_metabolite_to_pathway(hmdb):
    hete = KNode('HMDB:HMDB0011134', type=node_types.CHEMICAL_SUBSTANCE)
    results = hmdb.metabolite_to_pathway(hete)
    assert len(results) > 0
    node_ids=[node.id for edge,node in results]
    assert 'SMPDB:SMP00710' in node_ids

