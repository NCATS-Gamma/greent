import pytest
from SPARQLWrapper import SPARQLWrapper, JSON



@pytest.fixture()
def sparql_runner():
    blaze_url = 'https://stars-app.renci.org/uberongraph/sparql'
    return SPARQLWrapper(blaze_url)





def test_endpoint(sparql_runner : SPARQLWrapper ):
    sparql_runner.setQuery(
    """
            SELECT ?g
                WHERE {
                  Graph ?g {
                  }
                }    
     """
    )
    sparql_runner.setReturnFormat(JSON)
    results = sparql_runner.query().convert()
    assert (len(results.get('results', {}).get('bindings', {})))

