from greent.util import Text
from greent.synonymizers import oxo_synonymizer
from greent.util import LoggingUtil
from greent.graph_components import LabeledID
from builder.question import LabeledID
import logging

logger = LoggingUtil.init_logging(__name__, level=logging.DEBUG)

# Substances are a special case, because the landscape of identifiers is such a mess.
# Therefore, it's going to take a few different approaches in conjunction to get anywhere.
# If we start with a CTD:chemical, then we can get a MeSH from CTD, and go to OXO from there.
# If we have MeSH, UMLS, snomed, NCIT, Drugbank, CAS or CHEBI we can go to OXO to get the others
# From either CHEBI or DrugBank we can use UniChem to get CHEMBL.
# If we start with CHEMBL, on the other hand, then we can go to UniChem and then to OXO and CTD.
#
# This is all based on the idea that our two main methods of getting drug->gene are pharos and ctdbase.
# And these are also how we recognize names.  So if we get the name via pharos, then we have a CHEMBL id
# and convert UniChem,OXO,CTD. But if we got the name via CTD, then we go CTD,MeSh,OXO,UniChem
#
# If we add other drug name resolvers then things may change. Adding other functions that simply use compound ids
# should be ok, as long as these two paths resolve whatever the name of interest is.
#
# Sept 2019: Note now that having UniChem in here is no longer relevant.  We are pre-caching
# anything from unichem up front, so the on-the-fly stuff is not only not helpful, but
# potentially confusing.  Dropping it.
def synonymize(node,gt):
    logger.debug("Synonymize: {}".format(node.id))
    curie = Text.get_curie(node.id)
    synonyms = set()  
    if 'KEGG.COMPOUND' in node.id:
        kegg_un_namespaced = f'KEGG:{Text.un_curie(node.id)}'
        node.add_synonyms([LabeledID(identifier=kegg_un_namespaced, label=node.name)])
    synonyms.update(synonymize_with_OXO(node,gt))
    synonyms.update(kegg_id_normalize(node))
    return synonyms

def kegg_id_normalize(node):
    # sometimes OXO returns KEGG_COMPOUND instead of KEGG.COMPOUND and subsequent services are having trouble 
    # also if we find KEGG:C##### we should probably convert it to KEGG.COMPOUND
    filtered = list(filter(lambda x : 'KEGG_COMPOUND' in x.identifier or 'KEGG:C' in x.identifier, node.synonyms)   )    
    mapped = set(map(lambda x : LabeledID(identifier = x.identifier.replace('G_C','G.C') if 'G_C' in x else x.identifier.replace('KEGG:C','KEGG.COMPOUND:C') , label= x.label ),filtered))    
    return mapped

def synonymize_with_OXO(node,gt):
    return oxo_synonymizer.synonymize(node,gt)

def synonymize_with_UniChem(node,gt):
    logger.debug(" UniChem: {}".format(node.id))
    all_synonyms = set()
    for synonym in node.synonyms:
        logger.debug(f"  {synonym}")
        curie = Text.get_curie(synonym.identifier)
        logger.debug(f"    {curie}")
        if curie in ('CHEMBL', 'CHEBI', 'DRUGBANK', 'PUBCHEM'):
            new_synonyms = gt.unichem.get_synonyms( synonym.identifier )
            labeled_synonyms = [LabeledID(identifier=s, label=synonym.label) for s in new_synonyms]
            all_synonyms.update(labeled_synonyms)
    #node.add_synonyms( all_synonyms )
    return all_synonyms

