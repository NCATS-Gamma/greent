from greent.service import Service
from greent.triplestore import TripleStore
from greent.util import LoggingUtil
from greent.util import Text
from greent.graph_components import KEdge, KNode, LabeledID
from greent import node_types

logger = LoggingUtil.init_logging(__name__)

class ChemBioKS(Service):
    """ Generic service endpoints for medical and bio-chemical data. This set
        comprises portions of chem2bio2rdf (CTD, KEGG, PubChem, DRUGBANK) """

    def __init__(self, context): #triplestore):
        super(ChemBioKS, self).__init__("chembio", context)
        self.triplestore = TripleStore (self.url)

    def query_chembio (self, query):
        """ Execute and return the result of a SPARQL query. """
        return self.triplestore.execute_query (query)

    #Used in our lookup stuff
    def graph_drugname_to_pubchem( self, drugname_node):
            drug_name = Text.un_curie (drugname_node.id)
            response = self.drugname_to_pubchem(drug_name)
            predicate=LabeledID('rdfs:ID', 'identifies')
            results = []
            for r in response:
                node = KNode( "PUBCHEM:{}".format( r['drugID'].split('/')[-1]), node_types.DRUG, label=r['drugName'])
                edge = self.create_edge(drugname_node,node,'chembio.graph_drugname_to_pubchem',drugname_node.id,predicate)
                results.append( (edge,node) )
            return results

    ## GETS

    def get_exposure_conditions (self, chemicals):
        """ Identify conditions (MeSH IDs) triggered by the specified stressor
            agent ids (also MeSH IDs).

        :param chemicals: List of IDs for substances of interest.
        :type chemicals: list of MeSH IDs, eg. D052638
        """
        id_list = ' '.join (list(map (lambda d : "( mesh:{0} )".format (d),
                            chemicals)))
        text = self.triplestore.get_template ("ctd_gene_expo_disease").\
            safe_substitute (chemicals=id_list)
        results = self.triplestore.execute_query (text)
        return list(map (lambda b : {
            "chemical" : b['chemical'].value,
            "gene"     : b['gene'].value,
            "pathway"  : b['kegg_pathway'].value,
            "pathName" : b['pathway_name'].value,
            "pathID"   : b['pathway_id'].value,
            "human"    : '(human)' in b['pathway_name'].value
        },
                         results.bindings))

    def get_drugs_by_condition (self, conditions):
        """ Get drugs associated with a set of conditions.

        :param conditions: Conditions to find associated drugs for.
        :type conditions: List of MeSH IDs for conditions, eg.: D001249
        """
        if not isinstance (conditions,list):
            conditions = [ conditions ]

        conditions = list(map(lambda v : v.replace ("MESH:", "mesh:"), conditions))
        prefix = "mesh:"
        if any(map(lambda v : v.startswith(prefix), conditions)):
            prefix = ""
        condition_list = ', '.join (list(map (lambda d : " {0}{1} ".format (prefix, d) , conditions)))
        result = self.triplestore.query_template (
            inputs = { "diseaseIds" : condition_list.lower () },
            outputs = [ 'drugID', 'drugGenericName', 'pubChemCID', 'diseasePMIDs' ],
            template_text="""
            prefix mesh:           <http://bio2rdf.org/mesh:> 
            prefix ctd:            <http://chem2bio2rdf.org/ctd/resource/>
            prefix db_resource:    <http://chem2bio2rdf.org/drugbank/resource/>
            select ?drugID ?drugGenericName ?diseasePMIDs ?ctdChemDis ?pubChemCID where {
               values ( ?diseaseId ) { ( $diseaseIds ) }
               ?ctdChemDis  ctd:cid                        ?pubChemCID;
                            ctd:diseaseid                  ?diseaseId;
                            ctd:pubmedids                  ?diseasePMIDs.
               ?dbInter     db_resource:Name               ?name ;
	                    db_resource:DBID               ?drugID .
               ?drugID      db_resource:CID                ?pubChemCID ;
  	                    db_resource:Generic_Name       ?drugGenericName .
            }""")
        return result

    def get_drugs_by_condition_graph (self, conditions):
        drugs = self.get_drugs_by_condition (conditions.identifier)
        results = []
        predicate=LabeledID("RO:0002302", "is_treated_by_substance")
        for r in drugs:
            node = KNode (r['drugID'].split('/')[-1:][0], node_types.DRUG, r['drugGenericName'])
            edge = self.create_edge(conditions, node, 'chembio.get_drugs_by_condition_graph', conditions.identifier, predicate, publications= r['diseasePMIDS'])
            results.append ( (edge, node) )
        #logger.debug ("chembio drugs by condition: {}".format (results))
        return results

    def get_genes_pathways_by_disease (self, diseases):
        """ Get genes and pathways associated with specified conditions.

        :param diseases: List of conditions designated by MeSH ID.
        :return: Returns a list of dicts containing gene and path information.
        """
        diseaseMeshIDList = ' '.join (list(map (lambda d : "( mesh:{0} )".format (d), diseases)))
        text = self.triplestore.get_template ("genes_pathways_by_disease").safe_substitute (diseaseMeshIDList=diseaseMeshIDList)
        results = self.triplestore.execute_query (text)
        return list(map (lambda b : {
            "uniprotGene" : b['uniprotGeneID'].value,
            "keggPath"    : b['keggPath'].value,
            "pathName"    : b['pathwayName'].value,
            "human"       : '(human)' in b['pathwayName'].value
        },
        results.bindings))

    def get_drug_gene_disease (self, disease_name, drug_name):
        """ Identify targets and diseases assocaited with a drug name.
        :param disease_name: MeSH name of a disease condition.
        :type str: String
        :param drug_name: Name of a drug.
        :type str: String
        """
        text = self.triplestore.get_template ("drug_gene_disease").safe_substitute (
            diseaseName=disease_name,
            drugName=drug_name)
        results = self.triplestore.execute_query (text)
        return list(map (lambda b : {
            "uniprotSymbol" : b['uniprotSym'].value,
            "diseaseId"     : b['diseaseID'].value
        }, results.bindings))

    def pubchem_to_ncbigene (self, pubchemID):
        result = self.triplestore.query_template (
            inputs = { "pubchemID" : "pubchem:{}".format(pubchemID) },
            outputs = [ 'NCBIGene', 'meshID', 'interaction', 'interactionTypes', 'pubmedids' ],
            template_text="""
            prefix pubchem:        <http://chem2bio2rdf.org/pubchem/resource/pubchem_compound/>
            prefix ctd:            <http://chem2bio2rdf.org/ctd/resource/>
	    select distinct ?NCBIGene ?meshID ?interaction ?interactionTypes ?pubmedids where {
  		?ctdChemGene 	ctd:cid                     $pubchemID;
               			ctd:chemicalid              ?meshID ;
                                ctd:geneid                  ?NCBIGene;
                                ctd:interaction             ?interaction;
                                ctd:interactiontypes        ?interactionTypes;
                                ctd:pubmedids               ?pubmedids.
            }""")
        return list(map(lambda r : {
            'NCBIGene'   : r['NCBIGene'],
            'meshID'     : r['meshID'],
            'interaction': r['interaction'],
            'interactionTypes': r['interactionTypes'],
            'pubmedids'  : r['pubmedids']
        }, result))

    def drug_name_to_gene_symbol (self, drug_name):
        result = self.triplestore.query_template (
            inputs = { "drugName" : drug_name },
            outputs = [ 'uniprotSym', 'pmids', 'drugID' ],
            template_text="""
            prefix ctd:            <http://chem2bio2rdf.org/ctd/resource/>
            prefix db_resource:    <http://chem2bio2rdf.org/drugbank/resource/>
            select ?drugGenericName ?pmids ?drugID ?uniprotSym where {
               values ( ?drugName ) { ( "$drugName" ) }
               ?ctdChemGene ctd:cid                        ?pubChemCID;
                            ctd:pubmedids                  ?pmids;
                            ctd:gene                       ?uniprotSym .
               ?drugID      db_resource:CID                ?pubChemCID ;
  	                    db_resource:Generic_Name       ?drugGenericName .
               filter regex(lcase(str(?drugGenericName)), lcase(?drugName))
            }""")
        return list(map(lambda r : {
            'uniprotSym'   : r['uniprotSym'],
            'pmids'        : r.get('pmids', None),
            'drugID'       : r['drugID']
        }, result))

    def drugname_to_pubchem(self, drug_name):
        result = self.triplestore.query_template (
            inputs = { "drugName" : drug_name },
            outputs = [ 'pubChemID', 'drugGenericName' ],
            template_text="""
            prefix db_resource:    <http://chem2bio2rdf.org/drugbank/resource/>
            select distinct ?pubChemID ?drugGenericName where {
               values ( ?drugName ) { ( "$drugName" ) }
               ?drugID      db_resource:CID                ?pubChemID ;
  	                    db_resource:Generic_Name       ?drugGenericName .
               filter regex(lcase(str(?drugGenericName)), lcase(?drugName))
            }""")
        return list(map(lambda r : {
            'drugID'       : r['pubChemID'],
            'drugName'     : r['drugGenericName']
        }, result))

    def gene_symbol_to_pathway (self, uniprot_symbol):
        return self.triplestore.query_template (
            inputs = { "uniprotSymbol" : uniprot_symbol },
            outputs = [ "keggPath" ],
            template_text="""
            prefix kegg:           <http://chem2bio2rdf.org/kegg/resource/>
            prefix pharmgkb:       <http://chem2bio2rdf.org/pharmgkb/resource/>
            prefix ctd:            <http://chem2bio2rdf.org/ctd/resource/>
            select ?ctdGene ?uniprotID ?pathwayName ?keggPath where {
               values ( ?ctdGene ) { ( <$uniprotSymbol> ) }
               ?keggPath    kegg:protein    ?uniprotID ; kegg:Pathway_name ?pathwayName .
               ?pharmGene   pharmgkb:Symbol ?ctdGene ; pharmgkb:UniProt_Id ?uniprotID.
               ?ctdChemGene ctd:gene        ?ctdGene.
            } LIMIT 500
            """)

    def uniprot_to_hgnc (self, uniprot_symbol):
        return self.triplestore.query_template (
            inputs = { "uniprotID" : Text.un_curie (uniprot_symbol.identifier) },
            outputs = [ "hgncID" ],
            template_text="""
            prefix uniprot:    <http://chem2bio2rdf.org/uniprot/resource/gene/>
            prefix owl:        <http://www.w3.org/2002/07/owl#>
            prefix hgnc:       <http://chem2bio2rdf.org/rdf/resource/hgnc/>
            select distinct ?hgncID where {
               values ( ?uniprotID ) { ( uniprot:${uniprotID} ) }
               ?uniprotID <http://www.w3.org/2002/07/owl#sameAs> ?hgncID.
               filter ( strstarts (str(?hgncID), "http://bio2rdf.org/gene:"))
            }
            """)

    def graph_get_genes_by_disease (self, disease): #reasoner
        disease = disease.id.split (':')[1].lower ()
        response = self.get_genes_pathways_by_disease ([ disease ])
        results = []
        predicate=LabeledID("RO:0002326","contributes_to")
        for r in response:
            node = KNode ("UNIPROT:{0}".format (r['uniprotGene'].split('/')[-1:][0]),  node_types.GENE)
            edge = self.create_edge (node,disease,'chembio.graph_get_genes_by_disease',disease.id, predicate)
            results.append ( (edge, node) )
        return results

    def graph_get_pathways_by_gene (self, gene): #reasoner        
        response = self.triplestore.query_template (
            inputs = { "gene" : gene.id.split(':')[1].upper () },
            outputs = [ 'keggPath' ],
            template_text="""
            prefix kegg:      <http://chem2bio2rdf.org/kegg/resource/>
            prefix drugbank:  <http://chem2bio2rdf.org/drugbank/resource/>
            prefix uniprot:   <http://chem2bio2rdf.org/uniprot/resource/gene/>
            prefix ctd:       <http://chem2bio2rdf.org/ctd/resource/>
            prefix mesh:      <http://bio2rdf.org/mesh:>
            select ?drugGenericName ?uniprotGeneID ?pathwayName ?keggPath where {
               ?keggPath    kegg:protein                ?swissProtID ;
                            kegg:Pathway_name           ?pathwayName .
               ?keggInter   kegg:cid                    ?pubchemCID .
               ?dbInter     drugbank:GeneBank_ID        ?geneBankID ;
                            drugbank:SwissProt_ID       ?swissProtID ;
                            drugbank:gene               ?uniprotGeneID .
               ?drugID      drugbank:CID                ?pubchemCID ;
                            drugbank:Generic_Name       ?drugGenericName .
               ?ctd_disease ctd:diseaseid               ?diseaseID ;
                            ctd:cid                     ?pubchemCID .
               values ( ?uniprotGeneID ) {
                  ( uniprot:$gene )
               }
            } LIMIT 2000""")
        results = []
        predicate=LabeledID('RO:0000056', 'participates_in')
        for r in response:
            node = KNode ("KEGG:{0}".format (r['keggPath'].split('/')[-1:][0]), node_types.PATHWAY)
            edge = self.create_edge (gene,node,'chembio.graph_get_pathways_by_gene',gene.id, predicate)
            results.append ( (edge, node) )
        return results

    def graph_drugbank_to_uniprot (self, drugbank):
        response = self.triplestore.query_template (
            inputs = { "drugID" : "DB{0}".format (Text.un_curie (drugbank.identifier)) },
            outputs = [ "uniprotGeneID" ],
            template_text = """
            prefix drugbank:      <http://chem2bio2rdf.org/drugbank/resource/>
            prefix drugbank_drug: <http://chem2bio2rdf.org/drugbank/resource/drugbank_drug/>
            prefix ctd:           <http://chem2bio2rdf.org/ctd/resource/>
            select distinct ?uniprotGeneID where {
               values ( ?drugID ) { ( drugbank_drug:${drugID} ) }
               ?dbInter     drugbank:GeneBank_ID        ?geneBankID ;
                            drugbank:gene               ?uniprotGeneID .
               ?drugID      drugbank:CID                ?pubchemCID ;
                            drugbank:Generic_Name       ?drugGenericName .
               ?ctd_disease ctd:diseaseid               ?diseaseID ;
                            ctd:cid                     ?pubchemCID .
            }""")
        predicate=LabeledID('SIO:001257', 'chemical to gene association')
        results = []
        for r in response:
            node = KNode ("UNIPROT:{0}".format (r['uniprotGeneID'].split('/')[-1:][0]), node_types.GENE)
            edge = self.create_edge(drugbank,node,'chembio.graph_drugbank_to_uniprot',predicate, drugbank.id)
            results.append(edge,node)
        return results

    def graph_diseasename_to_uniprot (self, disease):
        results = []
        response = self.triplestore.query_template (
            inputs = { "diseaseName" : Text.un_curie (disease.id) },
            outputs = [ "pubChemCID" ],
            template_text = """
            prefix ctd: <http://chem2bio2rdf.org/ctd/resource/>
            select distinct ?pubChemCID where {
               values ( ?diseaseName ) { ( "$diseaseName" ) }
               ?ctdChemDis  ctd:cid         ?pubChemCID;
                            ctd:diseasename ?diseaseNameRec.
               filter regex(lcase(str(?diseaseNameRec)), lcase(?diseaseName))
            } LIMIT 1""")
        if len(response) > 0: # This is a disease.
            response = self.triplestore.query_template (
                inputs = { "diseaseName" : Text.un_curie(disease.id) },
                outputs = [ "disPmids", "chemPmids", "uniprotSym" ],
                template_text = """
                prefix ctd: <http://chem2bio2rdf.org/ctd/resource/>
                select ?disPmids ?ctdChemDis ?chemPmids ?uniprotSym ?diseaseId where {
                  values ( ?diseaseName ) { ( "$diseaseName" ) }
                  ?ctdChemGene ctd:cid         ?pubChemCID;
                               ctd:pubmedids   ?chemPmids;
                               ctd:gene        ?uniprotSym.
                  ?ctdChemDis  ctd:cid         ?pubChemCID;
                               ctd:diseaseid   ?diseaseId;
                               ctd:diseasename ?diseaseNameRec;
                               ctd:pubmedids   ?disPmids.
                  filter regex(lcase(str(?diseaseNameRec)), lcase(?diseaseName))
                } LIMIT 500""")
            predicate=LabeledID('NCIT:R176', 'disease to gene association')
            for r in response:
                chemPmids = r['chemPmids']
                disPmids = r['disPmids']
                pmids = chemPmids + "|" + disPmids
                node = KNode ("UNIPROT:{0}".format (r['uniprotSym'].split('/')[-1:][0]), node_types.GENE)
                edge = self.create_edge (disease,node, 'chembio.graph_diseasename_to_uniprot', disease.id,predicate,
                                         publications=pmids)
                results.append ( (edge, node) )
        return results

    def graph_diseaseid_to_uniprot (self, drugbank):
        print( drugbank.id.lower() )
        response = self.triplestore.query_template (
            inputs = { "diseaseID" : drugbank.id.lower () },
            outputs = [ "uniprotGeneID" ],
            template_text = """
            prefix drugbank:      <http://chem2bio2rdf.org/drugbank/resource/>
            prefix drugbank_drug: <http://chem2bio2rdf.org/drugbank/resource/drugbank_drug/>
            prefix ctd:           <http://chem2bio2rdf.org/ctd/resource/>
            prefix mesh.disease:          <http://bio2rdf.org/mesh:> 
            select distinct ?uniprotGeneID where {
               values ( ?diseaseID ) { ( $diseaseID ) }
               ?dbInter     drugbank:gene               ?uniprotGeneID .
               ?drugID      drugbank:CID                ?pubchemCID.
               ?ctd_disease ctd:diseaseid               ?diseaseID ;
                            ctd:cid                     ?pubchemCID .
            }""")
        predicate=LabeledID('NCIT:R176', 'disease to gene association')
        results = []
        for r in response:
            node = KNode ("UNIPROT:{0}".format (r['uniprotGeneID'].split('/')[-1:][0]), node_types.GENE)
            edge = self.create_edge(drugbank,node,'chembio.graph_diseaseid_to_uniprot',drugbank.id,predicate)
            results.append((edge,node))
        return results



    #       'NCBIGene'   : r['NCBIGene'],
    #        'meshID'     : r['meshID'],
    #        'interaction': r['interaction'],
    #        'interactionTypes': r['interactionTypes']
    #        'pubmedids'  : r['pubmedids']
    def graph_pubchem_to_ncbigene( self, pubchem_node):
        #The compound mesh coming back from here is very out of date.  Ignore.
        pubchemid = Text.un_curie (pubchem_node.id)
        response = self.pubchem_to_ncbigene(pubchemid)
        predicate=LabeledID('CTD:interacts_with', 'interacts')
        retvals = []
        for r in response:
            props = {}
            props['interaction'] = r['interaction']
            props['interactionTypes'] = r['interactionTypes']
            props['publications'] = r['pubmedids'].split('|')
            node = KNode( "NCBIGene:{}".format( r['NCBIGene']), node_types.GENE)
            edge = self.create_edge(pubchem_node, node,'chembio.graph_pubchem_to_ncbigene',pubchem_node.id,
                                    predicate,publications=[f'PMID:{x}' for x in r['pubmedids'].split('|')])
            retvals.append( (edge,node) )
        return retvals

