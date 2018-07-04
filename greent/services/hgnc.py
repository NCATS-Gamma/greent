import requests
from greent import node_types
from greent.graph_components import LabeledID
from greent.service import Service
from greent.util import LoggingUtil
from builder.question import LabeledThing

import time
import logging


#A map from identifiers.org namespaces (curie prefixes) to how HGNC describes these things
prefixes_to_hgnc = {
    'HGNC': 'hgnc_id',
    'NCBIGENE': 'entrez_id',
    'NCBIGene': 'entrez_id',
    'HGNC.SYMBOL': 'symbol',
    'OMIM': 'omim_id',
    #UNIPROTKB is not a identifiers.org prefix.  Uniprot is, and uniprot.isoform is.
    'UNIPROTKB': 'uniprot_ids',
    'UniProtKB': 'uniprot_ids',
    'ENSEMBL': 'ensembl_gene_id',
    #'RNAcentral': 'rna_central_ids' According to the docs, rna_central_ids should be supported but it is not.
}

hgnc_to_prefixes = { v: k for k,v in prefixes_to_hgnc.items()}

logger = LoggingUtil.init_logging(__name__, logging.DEBUG)

class HGNC(Service):

    """ Generic GENE id translation service. Essentially a highly generic synonym finder. """
    def __init__(self, context): 
        super(HGNC, self).__init__("hgnc", context)

    #TODO: share the retry logic in Service?
    def query(self,url,headers):
        """if the prefix is malformed, then you get a 400.  If the prefix is ok, but there is no data, you get
        a valid json response with no entries.  So failures here are most likely timeouts and stuff like that."""
        done = False
        num_tries = 0
        max_tries = 2
        wait_time = 5 # seconds
        logger.debug(f'Try {url}')
        while num_tries < max_tries:
            try:
                response = requests.get(url , headers= headers)
                return response.json()
            except Exception as e:
                logger.error(response)
                logger.error(f'Threw exception {e}')
                num_tries += 1
                time.sleep(wait_time)
        return None
        

    def  get_name(self, node):
        """Given a node for an hgnc, return the name for that id"""
        if node.node_type != node_types.GENE:
            raise ValueError('Node must be a gene')
        identifier_parts = node.identifier.split(':')
        if identifier_parts[0] == 'HGNC':
            query_string='hgnc_id'
        elif identifier_parts[0].upper() == 'NCBIGENE':
            query_string = 'entrez_id'
        else:
            raise ValueError('Node must represent an HGNC or NCBIGene id.')
        hgnc_id = identifier_parts[1]
        headers = {'Accept':'application/json'}
        try:
            r = self.query('%s/%s/%s' % (self.url, query_string, hgnc_id), headers= headers)
            symbol = r['response']['docs'][0]['symbol']
        except:
            #logger.warn(f"Problem retrieving name for {hgnc_id}")
            symbol = hgnc_id
        return symbol 

    def get_synonyms(self, identifier):
        #HGNC doesn't want to handle more than 10 of these a second (from one IP).  If we think that we're
        # going to be running in parallel, that means a simple wait should fix it.  ESPECIALLY, since we should
        # almost never be calling this - everything should be pre-cached.  So this little wait time, which is
        # terrible, should in the end not matter very much
        time.sleep(0.2)
        identifier_parts = identifier.split(':')
        prefix = identifier_parts[0]
        gid = identifier_parts[1]
        try:
            query_type = prefixes_to_hgnc[prefix]
        except KeyError:
            #logger.warn(f'HGNC does not handle prefix: {prefix}')
            return set()
        headers = {'Accept':'application/json'}
        r = self.query('%s/%s/%s' % (self.url, query_type, gid), headers= headers)
        try:
            docs = r['response']['docs']
        except:
            #didn't get anything useful
            logger.error("No good return")
            return set()
        synonyms = set()
        logger.debug(f"Number of docs: {len(docs)}")
        for doc in docs:
            #hgnc only returns an hgnc label (not eg. an entrez label)
            try:
                hgnc_label = doc['symbol']
            except:
                hgnc_label = None
            for key in doc:
                if key in hgnc_to_prefixes:
                    values = doc[key]
                    prefix = hgnc_to_prefixes[key]
                    if not isinstance(values, list):
                        values = [values]
                    for value in values:
                        if ':' in value:
                            value = value.split(':')[-1]
                        synonym = f'{prefix}:{value}'
                        synonyms.add(LabeledThing(identifier=synonym, label=hgnc_label))
        return synonyms


