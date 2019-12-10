import pytest
from greent.graph_components import KNode
from greent.services.uberongraph import UberonGraphKS
from greent.servicecontext import ServiceContext
from greent import node_types
from greent.util import Text
from greent.conftest import rosetta

@pytest.fixture()
def uberon(rosetta):
    uberon = rosetta.core.uberongraph
    return uberon

def test_chem(uberon):
    """This test is to point out that Verapamil is doing some funny stuff where it ahs a """
    chem = KNode('CHEBI:9948',type=node_types.CHEMICAL_SUBSTANCE, name="Verapamil")
    cc = uberon.get_chemical_by_chemical(chem)
    for edge,node in cc:
        print (edge.original_predicate,node)

def test_label(uberon):
    """Use ubergraph to get labels for ontology term"""
    mondo = 'MONDO:0001876'
    expected_label='renal artery atheroma'
    actual_label = uberon.get_label(mondo)
    assert actual_label == expected_label

def test_name(uberon):
    """Use ubergraph to get labels for ontology term"""
    cn ='CL:0000097'
    label = uberon.get_label( cn )
    assert 'mast cell' == label

def test_disease_to_go(uberon):    
    """Make sure that we get processes and activities for a disease, and all edges get mapped"""
    disease = KNode('MONDO:0009212',type=node_types.DISEASE, name="Congenital Factor X Deficiency")
    rp = uberon.get_process_by_disease( disease )
    ra = uberon.get_activity_by_disease( disease )
    r = rp + ra
    for ri in r:
        assert ri[0].standard_predicate.identifier != 'GAMMA:0'
    assert len(r) > 50

def test_pheno_to_go_2(uberon):
    """Make sure that we get processes and activities for a phenotype, and all edges get mapped"""
    disease = KNode('HP:0000141',type=node_types.PHENOTYPIC_FEATURE, name="Bronchitis")
    rp = uberon.get_process_by_phenotype( disease )
    ra = uberon.get_activity_by_phenotype( disease )
    r = rp + ra
    for ri in r:
        assert ri[0].standard_predicate.identifier != 'GAMMA:0'
    assert len(r) > 3

def test_cell_to_go(uberon):
    """Make sure that for a variety of cell types we 1) get relationships going both directions and
     that we map all predicates"""
    for cell in ('CL:0000121','CL:0000513', 'CL:0000233','CL:0000097', 'CL:0002251'):
        foundsub = False
        foundobj = False
        rp = uberon.get_process_by_anatomy( KNode(cell, type=node_types.CELL, name="some cell"))
        ra = uberon.get_activity_by_anatomy( KNode(cell, type=node_types.CELL, name="some cell"))
        r = ra + rp
        for ri in r:
            assert ri[0].standard_predicate.identifier != 'GAMMA:0'
            if ri[0].source_id == ri[1].id:
                foundsub = True
            elif ri[0].target_id == ri[1].id:
                foundobj = True
        assert foundsub, foundobj

def test_go_to_cell(uberon):
    """Check that we return cells for a particular process"""
    go = 'GO:0045576'
    r = uberon.get_anatomy_by_process_or_activity( KNode(go, type=node_types.BIOLOGICAL_PROCESS_OR_ACTIVITY, name="some term"))
    foundsub = False
    foundobj = False
    for ri in r:
        assert ri[0].standard_predicate.identifier != 'GAMMA:0'
        if ri[0].source_id == ri[1].id:
            if ri[1].id.startswith('CL'):
                foundsub = True
        elif ri[0].target_id == ri[1].id:
            if ri[1].id.startswith('CL'):
                foundobj = True
    #for this term, only GO->CL edges exist
    #assert foundsub
    assert foundobj


def test_cell_to_anatomy_super(uberon):
    """Check that we can go from cells to anatomical entities by finding that cells of the alimentary canal
    are part of the digestive system"""
    k = KNode('CL:0002251', type=node_types.CELL, name='epithelial cell of the alimentary canal')
    results = uberon.get_anatomy_by_anatomy_graph( k )
    #Should get back digestive system UBERON:0001007
    assert len(results) > 0
    idents = [ ke[1].id for ke in results ]
    assert 'UBERON:0001007' in idents


def test_cell_to_anatomy(uberon):
    """Check that we can go from cells to anatomical entities by finding that mast cells are part of the immune system"""
    k = KNode('CL:0000097', type=node_types.CELL)
    results = uberon.get_anatomy_by_anatomy_graph( k )
    #Mast cells are part of the immune system
    assert len(results) >= 1
    idents = [ ke[1].id for ke in results ]
    assert 'UBERON:0002405' in idents

def test_anatomy_to_cell(uberon):
    """Check anatomy->cell by showing that the immune system contains mast cells"""
    k = KNode('UBERON:0002405', type=node_types.ANATOMICAL_ENTITY, name='Immune system')
    results = uberon.get_anatomy_by_anatomy_graph( k )
    #Mast cells are part of the immune system
    assert len(results) > 0
    identifiers = [result[1].id for result in results]
    gotcells = False
    for identifier in identifiers:
        if identifier.startswith('CL:'):
            gotcells = True
    assert gotcells
    assert 'CL:0000097' in identifiers

def test_anatomy_to_cell_upcast(uberon):
    """Check cell->anatomy for smooth muscle cells"""
    k = KNode('CL:0000192', type=node_types.ANATOMICAL_ENTITY, name='Smooth Muscle Cell')
    results = uberon.get_anatomy_by_anatomy_graph( k )
    #There's no cell that's part of another cell?
    identifiers = [result[1].id for result in results]
    anat_identifiers = list( filter(lambda x: x.startswith('UBERON'), identifiers))
    assert len(anat_identifiers) > 0

def test_pheno_to_anatomy_ALS(uberon):
    """Phenotype -> anatomy.  Check that ALS -> various neurons and CNS"""
    #Arrhythmia occurs in...
    k = KNode('HP:0007354', type=node_types.PHENOTYPIC_FEATURE)
    results = uberon.get_anatomy_by_phenotype_graph( k )
    nodes = [n.id for e,n in results]
    assert 'CL:0002319' in nodes #neural cell
    assert 'CL:0000393' in nodes #electrically responsive cell
    assert 'UBERON:0001017' in nodes #central nervous system


def test_pheno_to_anatomy(uberon):
    """Test phenotype -> Anatomy,   Arrhythmia -> Circulatory and cardiovascular systems"""
    k = KNode('HP:0011675', type=node_types.PHENOTYPIC_FEATURE)
    results = uberon.get_anatomy_by_phenotype_graph( k )
    #anatomical features
    ntypes = set([n.type for e,n in results])
    assert len(ntypes) == 1
    assert node_types.ANATOMICAL_ENTITY in ntypes
    identifiers = [n.id for e,n in results]
    assert 'UBERON:0000468' in identifiers #multicellular organism (yikes)
    assert 'UBERON:0004535' in identifiers #cardiovascular system
    assert 'UBERON:0001009' in identifiers # circulatory system
    #These are no longer found, due to changes in HP
    #assert 'UBERON:0000948' in identifiers #heart
    #assert 'UBERON:0001981' in identifiers #blood vessel


def test_anat_to_pheno(uberon):
    """Anatomy -> Phenotypes.  Heart-> (several heart related phenotypes)"""
    k = KNode('UBERON:0000948', type=node_types.ANATOMICAL_ENTITY)
    results = uberon.get_phenotype_by_anatomy_graph( k )
    #phenos
    ntypes = set([n.type for e,n in results])
    assert len(ntypes) == 1
    assert node_types.PHENOTYPIC_FEATURE in ntypes
    identifiers = [n.id for e,n in results]
    for e,n in results:
        print( n.id, n.name )
    assert 'HP:0001750' in identifiers #single ventricle
    assert 'HP:0001644' in identifiers #dilated cardiomyopathy
    assert 'HP:0011672' in identifiers #cardiac myxoma

def test_non_HP_pheno_to_anatomy(uberon):
    """If the input node is not valid, return an empty result list"""
    k = KNode('xx:0011675', type=node_types.PHENOTYPIC_FEATURE)
    results = uberon.get_anatomy_by_phenotype_graph( k )
    assert len(results) == 0

def test_molecular_function_to_chemical(uberon):
    """Look up chemicals by function. acetyl-CoA metabolic process should have participant acetyl-CoA"""
    k = KNode('GO:0006084', type= node_types.CHEMICAL_SUBSTANCE)
    results = uberon.get_chemical_entity_by_process_or_activity(k)
    attributes = [(edge.target_id, edge.original_predicate, node.id, node.name) for edge, node in results]
    for edge_tar_id, predicate, node_id , node_name in attributes:
        assert edge_tar_id == node_id
    assert 'CHEBI:15351' in [ edge_tar_id for edge_tar_id, predicate, node_id , node_name in attributes ]
    assert 'acetyl-CoA' in [ node_name  for edge_tar_id, predicate, node_id , node_name in attributes ]
    assert ('RO:0000057','has participant') in [ predicate for edge_tar_id, predicate, node_id , node_name in attributes ]

def test_phenotype_to_biological_process_or_activity(uberon):
    """Look up processes for a phenotype.  THis abnormality of sulfur metabolismn should be related to  sulfur
    metabolic processes"""
    k = KNode('HP:0004339', type= node_types.PHENOTYPIC_FEATURE)
    presults = uberon.get_process_by_phenotype(k)
    aresults = uberon.get_activity_by_phenotype(k)
    results = presults + aresults
    for r in results:
        print(r[1].id, r[1].name)
    identifiers = [edge.target_id for edge, node in results]
    attributes = [(edge.target_id, edge.original_predicate, node.id, node.name) for edge, node in results]
    for edge_tar_id, predicate, node_id , node_name in attributes:
        assert edge_tar_id == node_id
    assert 'GO:0000096' in [ edge_tar_id for edge_tar_id, predicate, node_id , node_name in attributes ]
    assert 'GO:0006790' in [ edge_tar_id for edge_tar_id, predicate, node_id , node_name in attributes ]
    assert 'sulfur amino acid metabolic process' in [ node_name  for edge_tar_id, predicate, node_id , node_name in attributes ]
    assert 'sulfur compound metabolic process' in [ node_name  for edge_tar_id, predicate, node_id , node_name in attributes ]
    #both of these have the same relationship
    assert ('UPHENO:0000001', 'has phenotype affecting') in [ predicate for edge_tar_id, predicate, node_id , node_name in attributes ]
    
def test_disease_to_anatomy(uberon):
    """Look up anatomy connected to a disease.  "infection of lymph nodes in the axilla" """
    k = KNode('MONDO:0003070', type = node_types.DISEASE)
    results = uberon.get_anatomy_by_disease(k)
    identifiers = [edge.target_id for edge, node in results]
    attributes = [(edge.target_id, edge.original_predicate, node.id, node.name) for edge, node in results]
    for edge_tar_id, predicate, node_id , node_name in attributes:
        assert edge_tar_id == node_id
    
    assert 'UBERON:0001421' in [ edge_tar_id for edge_tar_id, predicate, node_id , node_name in attributes ]
    assert 'UBERON:0009472' in [ edge_tar_id for edge_tar_id, predicate, node_id , node_name in attributes ]
    assert 'UBERON:0007823' in [ edge_tar_id for edge_tar_id, predicate, node_id , node_name in attributes ]

    assert ('RO:0002410', 'causally related to') in [ predicate for edge_tar_id, predicate, node_id , node_name in attributes ]
    assert 'pectoral girdle region' in [ node_name  for edge_tar_id, predicate, node_id , node_name in attributes ]
    assert 'axilla' in [ node_name  for edge_tar_id, predicate, node_id , node_name in attributes ]
    assert 'appendage girdle region' in [ node_name  for edge_tar_id, predicate, node_id , node_name in attributes ]

def test_disease_to_anatomy_rc_face(uberon):
    """disease->anatomy  retinal ciliopathy due to bardet-biedl -> retina"""
    k = KNode('MONDO:0022407', type = node_types.DISEASE)
    results = uberon.get_anatomy_by_disease(k)
    newnodes = [ node.id for edge,node in results ]
    assert 'UBERON:0001456' in newnodes

def test_cell_component_to_chemical(uberon):
    """Cellular component -> chemicals. Laminin-8 complex -> """
    k = KNode('GO:0043257', type = node_types.CELLULAR_COMPONENT)
    results = uberon.get_chemical_substance_by_anatomy(k)
    identifiers = [edge.target_id for edge, node in results]
    attributes = [(edge.target_id, edge.original_predicate, node.id, node.name) for edge, node in results]
    for edge_tar_id, predicate, node_id , node_name in attributes:
        assert edge_tar_id == node_id
    nidentifiers = [node.target_id for edge, node in results]
    assert 'CHEBI:37622' in nidentifiers #carboxoamide
    assert 'CHEBI:15841' in nidentifiers #polypeptide

def test_cell_component_to_anatomy(uberon):
    """Component -> anatomy. Neuron projection membrane -> embryonic structure"""
    k = KNode('GO:0032589', type = node_types.CELLULAR_COMPONENT)
    results = uberon.get_anatomy_by_anatomy_graph(k)
    identifiers =  [edge.target_id for edge, node in results]
    assert 'UBERON:0002050' in identifiers

def test_cell_component_to_disease(uberon):
    """Component -> disease.  Plasma membrane region -> rippling muscle disease 1"""
    k = KNode('GO:0098590', type = node_types.CELLULAR_COMPONENT)
    results = uberon.get_disease_by_anatomy_graph(k)
    identifiers =  [edge.target_id for edge, node in results]
    attributes = [(edge.target_id,edge.source_id, edge.original_predicate, node.id, node.name) for edge, node in results]
    for edge_tar_id, edge_source_id, predicate, node_id , node_name in attributes:
        assert edge_tar_id == k.id
    assert 'MONDO:0010868' in [edge_source_id for edge_tar_id,edge_source_id,  predicate, node_id , node_name in attributes ]

def test_cell_component_to_cell(uberon):
    """Cell component -> cell.   dendrite membrane -> neuron"""
    k = KNode('GO:0032590', type = node_types.CELLULAR_COMPONENT)
    results = uberon.get_anatomy_by_anatomy_graph(k)
    identifiers =  [edge.target_id for edge, node in results]
    assert 'CL:0000540' in identifiers

def test_neutrophil_to_phenotype(uberon):
    """cell->phenotype.  Neutrophils are associated with neutropenia"""
    neutrophil = KNode('CL:0000775',  type=node_types.ANATOMICAL_ENTITY, name = 'neutrophils')
    results = uberon.get_phenotype_by_anatomy_graph(neutrophil)
    neutropenia = 'HP:0001875'
    node_ids = [node.id for edge, node in results]
    source_ids = [edge.source_id for edge, node in results]
    assert len(source_ids) == len(node_ids)
    for x in node_ids:
        assert x in source_ids
    assert neutropenia in source_ids


def test_neutropenia_to_anatomy(uberon):
    """and neutropenia is associated with neutrophils"""
    neutropenia = KNode('HP:0001875', type= node_types.PHENOTYPIC_FEATURE, name = 'neutropenia')
    results = uberon.get_anatomy_by_phenotype_graph(neutropenia)
    neutrophil = 'CL:0000775'
    node_ids = [node.id for edge, node in results]
    target_ids = [edge.target_id for edge, node in results]
    assert len(target_ids) == len(node_ids)
    for x in node_ids:
        assert x in target_ids
    assert neutrophil in target_ids
