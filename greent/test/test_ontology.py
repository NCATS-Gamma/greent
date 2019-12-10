import pytest
import requests
import os
from greent.services.ontology import GenericOntology
from greent.servicecontext import ServiceContext

@pytest.fixture(scope='module')
def ontology():
    url = "http://purl.obolibrary.org/obo/mondo.obo"
    ontology_file = "mondo.obo"
    if not os.path.exists (ontology_file):
        r = requests.get(url, stream=True)
        with open(ontology_file, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024): 
                if chunk: # filter out keep-alive new chunks
                    f.write(chunk)
    return GenericOntology(ServiceContext.create_context(),
                           ontology_file)

def test_label(ontology):
    """Retrieve label for ontology term"""
    assert ontology.label('MONDO:0005737') == "Ebola hemorrhagic fever"

def test_is_a(ontology):
    """Check whether one term is a subclass of another"""
    assert ontology.is_a('MONDO:0005737', 'MONDO:0005762')

def test_xrefs(ontology):
    """Access db xrefs of an ontology term"""
    xrefs = ontology.xrefs('MONDO:0005737')
    xref_ids = [ x['id'] for x in xrefs ]
    print (xref_ids)
    for i in [ "DOID:4325", "EFO:0007243", "ICD10:A98.4", "MedDRA:10014071", "MESH:D019142", "NCIT:C36171", "Orphanet:319218", "SCTID:37109004", "UMLS:C0282687" ]:
        assert i in xref_ids

def test_synonyms(ontology):
    """Access equivalent IDs.  This will mostly work for MONDO. Other ontologies are less clear about equivalence."""
    syns = ontology.synonyms ('MONDO:0005737')
    received = []
    for s in syns:
        received = received + s.xref
    for expected in [ "DOID:4325",
                      "Orphanet:319218",
                      "NCIT:C36171" ]:
        assert expected in received

def test_search(ontology):
    """Look up terms via name.  It's in the interface, but we get better results in other ways"""
    result = ontology.search ('ebola', ignore_case=True)
    assert result[0]['id'] == 'MONDO:0005737'

def test_lookup(ontology):
    """Look up terms via equivalent ID.  It's in the interface, but we get better results in other ways"""
    result = ontology.lookup ('UMLS:C0282687')
    assert result[0]['id'] == 'MONDO:0005737'
