import pytest
from greent.services.uniprot import UniProt
from greent.servicecontext import ServiceContext
from greent.util import Text

@pytest.fixture(scope='module')
def uniprot():
    uniprot = UniProt(ServiceContext.create_context())
    return uniprot

#We are no longer including TREMBL in our synonyms. 

def test_uniprot_both(uniprot):
    """Call uniprot with a tremble id and get no synonyms"""
    uni = 'UniProtKB:A0A024QZH5'
    results = uniprot.get_synonyms(uni)
    assert len(results) == 0
    #assert results[0] == 'NCBIGene:56848'

def test_uniprot_fail(uniprot):
    """Call uniprot with a tremble id and get no synonyms"""
    uni = 'UniProtKB:A0A024QZH5'
    ncbis = uniprot.uniprot_2_ncbi(uni)
    assert len(ncbis) == 1
    hgncs = uniprot.uniprot_2_hgnc(uni)
    assert len(hgncs) == 0
    assert ncbis[0] == 'NCBIGene:56848'

def test_uniprot(uniprot):
    """Call uniprot with a tremble id and get no synonyms"""
    uni = 'UniProtKB:A0A096LNX8'
    hgncs = uniprot.uniprot_2_hgnc(uni)
    assert len(hgncs) == 0

