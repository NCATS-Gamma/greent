import pytest
from greent.graph_components import KNode
#from greent.services.biolink import Biolink
#from greent.ontologies.mondo import Mondo
#from greent.servicecontext import ServiceContext
from greent import node_types
from greent.util import Text
from greent.conftest import rosetta


@pytest.fixture()
def biolink(rosetta):
    #biolink = Biolink(ServiceContext.create_context())
    biolink = rosetta.core.biolink
    return biolink

@pytest.fixture()
def mondo(rosetta):
    #checker = Mondo(ServiceContext.create_context())
    checker = rosetta.core.checker
    return checker

#just cut out while waiting for monarch to be fixed
def _test_bad_gene_to_process(biolink):
    """Ensure that a bogus gene produces an empty result set when used to query for processs"""
    BAD_protein = KNode('UniProtKB:XXXXXX', type=node_types.GENE)
    results = biolink.gene_get_process_or_function(BAD_protein)
    assert len(results) == 0


def test_gene_to_disease(biolink):
    """Check that gene HBB is associated with a number of diseases,
    Check that Sickle Cell Disease is one of them
    Check that the correct gene/disease relationship is chosen as the predicate"""
    relations = biolink.gene_get_disease(KNode('HGNC:4827', type=node_types.GENE))
    assert len(relations) > 20 and len(relations) < 40
    identifiers = [node.id for r,node in relations]
    #everthing should be MONDO ids
    for ident in identifiers:
        assert Text.get_curie(ident) == 'MONDO'
    #Sickle cell should be in there.
    assert 'MONDO:0011382' in identifiers
    predicates = [ relation.standard_predicate for relation,n in relations ] 
    pids = set( [p.identifier for p in predicates] )
    plabels = set( [p.label for p in predicates] )
    assert 'RO:0002326' in pids


#just cut out while waiting for monarch to be fixed
def _test_gene_to_process(biolink):
    """The gene -> process/function service in the biolink api only works correctly if given
    a UniProtKB entry.  HGNC, which could be transformed server side, don't produce the same
    result, which this test checks.  HGNC in produces zero results.  If this test fails then it
    means that the translation is now being properly handled server side, and the client
    could be simplified."""
    KIT_protein = KNode('HGNC:6432', type=node_types.GENE)
    results = biolink.gene_get_process_or_function(KIT_protein)
    assert len(results) == 0
    for ke, kn in results:
        assert kn.type == node_types.BIOLOGICAL_PROCESS_OR_ACTIVITY
        assert Text.get_curie(kn.id) == "GO"

def _test_gene_to_process2(biolink):
    """Check that for NR1I3, we retrieve functions and processes.
    Spot check that a particular function, and a particular process are returned.
    Check that the node is returned with the correct type and that the returned terms are from GO"""
    NR1I3_protein = KNode('UniProtKB:Q14994', type=node_types.GENE)
    results = biolink.gene_get_process_or_function(NR1I3_protein)
    identifiers = [kn.id for ke,kn in results]
    assert len(identifiers) > 0
    assert 'GO:0000976' in identifiers
    assert 'GO:0071222' in identifiers
    for ke, kn in results:
        assert kn.type == node_types.BIOLOGICAL_PROCESS_OR_ACTIVITY
        assert Text.get_curie(kn.id) == "GO"

def test_disease_to_phenotypes_pmid_parsing(biolink):
    """Check for phenotypes of Marfan syndrome, and ensure that supporting
    pubmed identifiers are properly formatted.  Noting that sometimes a MONDO is returned
    as a phenotype as well (as is the case for Marfan, where inguinal hernia is returned
    with a MONDO identifier)"""
    disease = KNode('MONDO:0007947', type=node_types.DISEASE)
    results = biolink.disease_get_phenotype(disease)
    identifiers = [node.id for r,node in results]
    #everthing should be HP ids
    for ident in identifiers:
        assert Text.get_curie(ident) in ['HP','MONDO']
    pmids = [ edge.publications for edge,n in results if len(edge.publications) > 0]
    assert len(pmids) > 0
    pmid_set = set([item for sublist in pmids for item in sublist])
    assert len(pmid_set) > 0
    for pmid in pmid_set:
        assert pmid.startswith('PMID:')

#biolink has removed most of its common disease/phenotype links. so this now returns 0 results 12/6/19
def test_disease_to_phenotypes(biolink):
    #This tests pagination as well
    asthma = KNode('DOID:2841', type=node_types.DISEASE)
    results = biolink.disease_get_phenotype(asthma)
    assert len(results) == 0

def test_pathways(biolink):
    """Spot check that going from gene->pathway->gene returns the original input gene."""
    gene_id = 'HGNC:5013'
    gene = KNode(gene_id, type=node_types.GENE)
    results = biolink.gene_get_pathways(gene)
    for e, k in results:
        assert k.type == node_types.PATHWAY
    e,k = results[0]
    presults = biolink.pathway_get_gene(k)
    #Just check for one result
    for pe,pk in presults:
        assert pk.type == node_types.GENE
    gene_ids = [ pk.id for pe,pk in presults ]
    assert gene_id in gene_ids

def test_disease_to_gene(biolink):
    """Spot check looking up genes by disease (Downs syndrome)"""
    disease = KNode('DOID:14250', type=node_types.DISEASE, name="Downs Syndrome")
    results = biolink.disease_get_gene(disease)
    assert len(results) == 2 # Downs syndrome now has 2 Gene associations
    for e, k in results:
        assert k.type == node_types.GENE

def test_gene_to_phenotype(biolink):
    """Spot check that looking up phenotypes associated with gene APOE includes LDL measurement"""
    gene = KNode('HGNC:613', type=node_types.GENE, name="APOE")
    results = biolink.gene_get_phenotype(gene)
    assert len(results) > 150
    for e, k in results:
        assert k.type == node_types.PHENOTYPIC_FEATURE
    pheno_ids = [pheno_node.id for edge, pheno_node in results]
    assert 'EFO:0004611' in pheno_ids

def test_phenotype_to_gene(biolink):
    "Spot check looking up genes by phenotype"
    phenotype = KNode('HP:0000723', type=node_types.PHENOTYPIC_FEATURE, name="Restrictive Behaviour")
    results = biolink.phenotype_get_gene(phenotype)
    assert len(results) == 3
    for e, k in results:
        assert k.type == node_types.GENE
    gene_ids = [gene_node.id for edge, gene_node in results]
    assert "HGNC:9508" in gene_ids # some random gene that should be there