from greent.graph_components import KNode
from greent import node_types
from greent.conftest import rosetta

"""
The cache tests simply check for certain keys in the configured cache.  If this is pointing at the production cache,
it checks that the omnicorp cache is nominally correct, and spot checks several synonym and function calls.
"""

def test_omnicorp(rosetta):
    """Ensure that OmnicorpPrefixes have been loaded.  This key provides information about which pairs of prefixes
    have been put into the cache."""
    pref = rosetta.cache.get('OmnicorpPrefixes')
    assert len(pref) > 10

def test_omnicorp_2(rosetta):
    """Check that there are papers connecting Albuterol and CXCL8, and the list is properly prefixed"""
    pref = rosetta.cache.get('OmnicorpSupport(CHEBI:2549,HGNC:6025)')
    assert len(pref) > 0
    for p in pref:
        assert p.startswith('PMID')

def test_chebi(rosetta):
    """Check that CHEBI has been synonymized"""
    syns = rosetta.cache.get("synonymize(CHEBI:15366)")
    assert len(syns) > 0

def test_cache(rosetta):
    """Check that HGNC has been synonymized"""
    syns = rosetta.cache.get("synonymize(HGNC:795)")
    assert len(syns) > 0

def test_pharos_key(rosetta):
    """Check that pharos disease->gene has run"""
    key='pharos.disease_get_gene(MONDO:0008903)'
    res = rosetta.cache.get(key)
    assert len(res) > 0

def test_check_fanc_pheno(rosetta):
    """Check that biolink disease->phenotype has run"""
    key='biolink.disease_get_phenotype(MONDO:0019391)'
    s3 = rosetta.cache.get(key)
    assert len(s3) > 0

def test_norcodeine_enzymes(rosetta):
    """Test that kegg chemical->gene ran"""
    key='caster.input_filter(kegg~chemical_get_enzyme,metabolite)(CHEBI:80579)'
    s3 = rosetta.cache.get(key)
    assert s3 is not None

