import requests
import urllib
from greent.service import Service
from greent.ontologies.mondo import Mondo
from greent.ontologies.go import GO
from greent.ontologies.mondo2 import Mondo2
from greent.ontologies.go2 import GO2
from greent.util import Text
from greent.graph_components import KNode, KEdge,LabeledID
from greent import node_types
from datetime import datetime as dt
import logging


class Biolink(Service):
    """ Preliminary interface to Biolink. Will move to automated Translator Registry invocation over time. """

    def __init__(self, context):
        super(Biolink, self).__init__("biolink", context)
        self.checker = context.core.mondo
        self.go = context.core.go
        self.label2id = {'colocalizes_with': 'RO:0002325', 'contributes_to': 'RO:0002326'}

        
    def process_associations(self, r, function, target_node_type, input_identifier, url, input_node, reverse=False):
        """Given a response from biolink, create our edge and node structures.
        Sometimes (as in pathway->Genes) biolink returns the query as the object, rather
        than the subject.  reverse=True will handle this case, bringing back the subject
        of the response, rather than the object.  Fortunately, it looks like this is just per-function.
        We could instead try to see if the subject id matched our input id, etc... if the same
        function sometimes spun things around."""
        edge_nodes = []
        for association in r['associations']:
            pubs = []
            if 'publications' in association and association['publications'] is not None:
                for pub in association['publications']:
                    # Sometimes, we get back something like "uniprotkb" instead of a PMID.  We don't want it.
                    pubid_prefix = pub['id'][:4].upper()
                    if pubid_prefix == 'PMID':
                        pubs.append(pub['id'])
            if reverse:
                source_node = KNode(association['subject']['id'], target_node_type, association['subject']['label'])
                target_node = input_node
                newnode = source_node
            else:
                target_node = KNode(association['object']['id'], target_node_type, association['object']['label'])
                source_node = input_node
                newnode = target_node
            #Deal with biolink's occasional propensity to return Null relations
            # This basically happens only with the gene_get_function call, so if that gets fixed, we might be
            # able to make this a little nicer
            predicate_id = association['relation']['id']
            if (predicate_id is None):
                predicate_id = f'biolink:{function}'
            elif (':' not in predicate_id):
                if predicate_id in self.label2id:
                    predicate_id = self.label2id[predicate_id]
                else:
                    logging.getLogger('application').error(f'Relationship Missing: {predicate_id}')
                    predicate_id = f'biolink:{function}'
            predicate_label= association['relation']['label']
            if predicate_label is None:
                predicate_label = f'biolink:{function}'
            #now back to the show
            predicate = LabeledID(identifier=predicate_id,label= predicate_label)
            edge = self.create_edge(source_node, target_node, f'biolink.{function}',  input_identifier, predicate,  publications = pubs, url = url)
            edge_nodes.append((edge, newnode))
        return edge_nodes


    def gene_get_disease(self, gene_node):
        """Given a gene specified as a curie, return associated diseases."""
        #Biolink is pretty forgiving on gene inputs, and our genes should have HGNC as their identifiers nearly always
        ehgnc = urllib.parse.quote_plus(gene_node.identifier)
        logging.getLogger('application').debug('          biolink: %s/bioentity/gene/%s/diseases' % (self.url, ehgnc))
        urlcall = '%s/bioentity/gene/%s/diseases' % (self.url, ehgnc)
        r = requests.get(urlcall).json()
        return self.process_associations(r, 'gene_get_disease', node_types.DISEASE, ehgnc, urlcall, gene_node)

    def disease_get_phenotype(self, disease):
        #Biolink should understand any of our disease inputs here.
        url = "{0}/bioentity/disease/{1}/phenotypes/".format(self.url, disease.identifier)
        response = requests.get(url).json()
        return self.process_associations(response, 'disease_get_phenotype', node_types.PHENOTYPE, disease.identifier, url, disease)

    def gene_get_go(self, gene):
        # this function is very finicky.  gene must be in uniprotkb, and the curie prefix must be correctly capitalized
        uniprot_id = None
        for gene_synonym in gene.synonyms:
            curie = Text.get_curie(gene_synonym)
            if curie == 'UNIPROTKB':
                uniprot_id = gene_synonym
                break
        if uniprot_id is None:
            return []
        url = "{0}/bioentity/gene/UniProtKB:{1}/function/".format(self.url, Text.un_curie(uniprot_id))
        response = requests.get(url).json()
        return response,url,uniprot_id
        #return self.process_associations(response, 'gene_get_go', node_types.PROCESS, url)

    #Now I just have the higher-level version, and I can always get to these versions using caster
    '''
    def gene_get_function(self, gene):
        response,url,input_id = self.gene_get_go(gene)
        edges_nodes = self.process_associations(response, 'gene_get_function', node_types.FUNCTION, input_id, url,gene)
        function_results = list(filter(lambda x: self.go.is_molecular_function(x[1].identifier), edges_nodes))
        return function_results

    def gene_get_process(self, gene):
        response,url,input_id = self.gene_get_go(gene)
        edges_nodes = self.process_associations(response, 'gene_get_process', node_types.PROCESS, input_id, url,gene)
        process_results = list(filter(lambda x: self.go.is_biological_process(x[1].identifier), edges_nodes))
        return process_results
    '''

    def gene_get_process_or_function(self,gene):
        response,url,input_id = self.gene_get_go(gene)
        edges_nodes = self.process_associations(response, 'gene_get_process_or_function', node_types.PROCESS_OR_FUNCTION, input_id, url,gene)
        process_or_function_results = list(filter(lambda x: self.go.is_biological_process(x[1].identifier) or
                                                  self.go.is_molecular_function(x[1].identifier), edges_nodes))
        return process_or_function_results

    def gene_get_pathways(self, gene):
        url = "{0}/bioentity/gene/{1}/pathways/".format(self.url, gene.identifier)
        response = requests.get(url).json()
        return self.process_associations(response, 'gene_get_pathways', node_types.PATHWAY, gene.identifier, url,gene)

    def pathway_get_gene(self, pathway):
        url = "{0}/bioentity/pathway/{1}/genes/".format(self.url, pathway.identifier)
        response = requests.get(url).json()
        return self.process_associations(response, 'pathway_get_genes', node_types.GENE, url, pathway.identifier, pathway, reverse=True)
