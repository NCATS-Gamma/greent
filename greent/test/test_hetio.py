import pytest
from greent.graph_components import KNode
#from greent.services.biolink import Biolink
#from greent.ontologies.mondo import Mondo
#from greent.servicecontext import ServiceContext
from greent import node_types
from greent.util import Text
from greent.conftest import rosetta


@pytest.fixture()
def hetio(rosetta):
    hetio = rosetta.core.hetio
    return hetio

#NOTE THAT in hetio, genes are identified with integers.  These integers are NCBIGENE identifiers, but with no
# prefix, or url or anything.

def test_gene_to_anatomy(hetio):
    """Check that the gene LONP is related to 10-20 anatomy terms, which are all uberons, one of which is the digestive system """
    relations = hetio.gene_to_anatomy(KNode('NCBIGENE:83752', type=node_types.GENE))
    assert len(relations) < 20 and len(relations) > 10
    identifiers = [node.id for r,node in relations]
    #everything should be UBERON ids
    for ident in identifiers:
        assert Text.get_curie(ident) == 'UBERON'
    assert 'UBERON:0001007' in identifiers

def test_anatomy_to_gene(hetio):
    """Check that the digestiv system is related to genes, and one of them is LONP"""
    relations = hetio.anatomy_to_gene(KNode('UBERON:0001007', type=node_types.ANATOMICAL_ENTITY))
    nts = [node.type for r,node in relations]
    for nt in nts:
        assert nt == node_types.GENE
    identifiers = [node.id for r,node in relations]
    for ident in identifiers:
        assert Text.get_curie(ident) == 'NCBIGENE'
    assert 'NCBIGENE:83752' in identifiers


def test_gene_to_disease(hetio):
    """Test gene to disease association, by spot checking that KRT7 is associated with bile duct cancer"""
    relations = hetio.gene_to_disease(KNode('NCBIGENE:3855', type=node_types.GENE))
    assert len(relations) < 20 and len(relations) > 10
    identifiers = [node.id for r,node in relations]
    #everything should be UBERON ids
    for ident in identifiers:
        assert Text.get_curie(ident) == 'DOID'
    assert 'DOID:4606' in identifiers

def test_disease_to_symptom(hetio):
    """Test disease to pheno association, by spot checking that Crohn's is associated with skin manifestations"""
    #Crohn's disease has associated Skin Manifesations?
    relations = hetio.disease_to_phenotype(KNode('DOID:8778', type=node_types.DISEASE))
    identifiers = [node.id for r,node in relations]
    #everything should be UBERON ids
    for ident in identifiers:
        assert Text.get_curie(ident) == 'MESH'
    assert 'MESH:D012877' in identifiers
