import pytest
from greent.services.oxo import OXO
from greent.servicecontext import ServiceContext
from greent import node_types
#from greent.util import Text
from greent.conftest import rosetta
from greent.graph_components import KNode

"""OXO is a nice service for accessing db xrefs.  But we are going to use ubergraph or the ontologies directly in
the future. So this set of tests may soon be removed."""

@pytest.fixture(scope='module')
def oxo():
    oxo = OXO(ServiceContext.create_context())
    return oxo

def test_prefixes(oxo):
    """check that the oxo client can handle specific curie prefixes. Case insensitive"""
    assert oxo.is_valid_curie_prefix("EFO")
    assert oxo.is_valid_curie_prefix("NCBIGENE")
    assert oxo.is_valid_curie_prefix("NCBIGene")
    assert oxo.is_valid_curie_prefix("DOID")
    assert oxo.is_valid_curie_prefix("DoiD")
    assert oxo.is_valid_curie_prefix("MESH")
    assert oxo.is_valid_curie_prefix("MeSH")
    assert oxo.is_valid_curie_prefix("MONDO") #surprise!
    assert not oxo.is_valid_curie_prefix("dummy")

def test_bogus_syn(oxo):
    """Check that we get back no synonyms for a fake curie"""
    curieset = oxo.get_synonymous_curies('EFO:9999999')
    assert len(curieset) == 0


def test_synonyms(oxo):
    """Spot check EFO->other disease ontologies"""
    curieset = oxo.get_synonymous_curies('EFO:0000764')
    #A bunch of stuff comes back. We'll spot check a few
    assert 'MeSH:D015658' in curieset
    assert 'DOID:526' in curieset
    assert 'UMLS:C0019682' in curieset

def test_synonyms_stuff(oxo):
    """Assert that we return labels"""
    all_results = oxo.get_synonyms('EFO:0000764')
    assert len(all_results) > 0
    for result in all_results:
        assert 'label' in result

def test_synonyms_hp(oxo):
    """Assert that we get results with labels for an HP input"""
    all_results = oxo.get_synonyms('HP:0000726')
    assert len(all_results) > 0
    for result in all_results:
        assert 'label' in result


