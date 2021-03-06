import requests
from greent.service import Service
import time


class UniProt(Service):

    """ Generic GENE id translation service. Essentially a highly generic synonym finder. """
    def __init__(self, context): 
        super(UniProt, self).__init__("uniprot", context)

    #TODO: share the retry logic in Service?
    def query(self,url,data):
        """if the prefix is malformed, then you get a 400.  If the prefix is ok, but there is no data, you get
        a valid json response with no entries.  So failures here are most likely timeouts and stuff like that."""
        done = False
        num_tries = 0
        max_tries = 10
        wait_time = 5 # seconds
        while num_tries < max_tries:
            try:
                #TODO: This is bad form and will generate warnings.
                #We are only doing it because UniProt has an error with one of their servers
                # returning a crappy SSL certificate.  Once they fix that, we will remove the
                # verify=False flag.
                #return requests.post(url , data =data, verify=False)
                # The bad server has supposedly been removed.
                return requests.post(url , data =data)
            except Exception as e:
                print(e)
                num_tries += 1
                time.sleep(wait_time)
        return None


    ###
    #
    #  Originally, we were identifiying proteins and genes together.  But we don't want to do that.  Instead, we
    #  only want to get other protein identifiers.   Now, at the moment, we're only dealing with top-level UniProt
    #  identifiers (not isoforms, or subsequences like PRO markers).  We've decided on a list of identifiers that
    #  UniProt provides that map nicely to those things: MINT, neXtPROT, STRING.  Also, the protein ontology uses
    #  UniProt ids (different prefix) for SwissProt, but not for Trembl (those annoying A0A0 things)
    #
    #  So uniprot_2_hgnc and uniprot_2_ensembl are deprecated in terms of calculating synonyms, but we might want to
    #  build gene/protein relationships from them.
    #
    ##
    def uniprot_2_hgnc(self, identifier):
        """Some services, like quickgo, return uniprot identifiers that other services have a hard time
        interpreting.  Things like UniProtKB:A0A0A0MR54
        But UniProt knows what they are and can convert them into something else."""
        identifier_parts = identifier.split(':')
        upkb = identifier_parts[1]
        data = {'from'  : 'ACC+ID',
                'to'    : 'HGNC_ID',
                'format': 'tab',
                'query' : upkb }
        r = self.query(self.url, data=data)
        lines = r.text.split("\n")
        answerlines = list(filter( lambda x: x.startswith(upkb), lines))
        answerparts = [ x.strip().split()[-1] for x in answerlines ]
        return answerparts

    def uniprot_2_ncbi(self, identifier):
        """Some services, like quickgo, return uniprot identifiers that other services have a hard time
        interpreting.  Things like UniProtKB:A0A0A0MR54
        But UniProt knows what they are and can convert them into something else."""
        identifier_parts = identifier.split(':')
        upkb = identifier_parts[1]
        data = {'from'  : 'ACC+ID',
                'to'    : 'P_ENTREZGENEID',
                'format': 'tab',
                'query' : upkb }
        r = self.query(self.url, data=data)
        lines = r.text.split("\n")
        answerlines = list(filter( lambda x: x.startswith(upkb), lines))
        answerparts = [ f'NCBIGene:{x.strip().split()[-1]}' for x in answerlines ]
        return answerparts

    def uniprot_2_something(self,identifier,something):
        #A map going from the uniprot query to our prefix for that
        smap = {'STRING':'STRING','neXtProt':'neXtProt'}
        identifier_parts = identifier.split(':')
        upkb = identifier_parts[1]
        data = {'from'  : 'ACC+ID',
                'to'    : 'something',
                'format': 'tab',
                'query' : upkb }
        r = self.query(self.url, data=data)
        lines = r.text.split("\n")
        answerlines = list(filter( lambda x: x.startswith(upkb), lines))
        answerparts = [ f'{smap[something]}:{x.strip().split()[-1]}' for x in answerlines ]
        return answerparts


    def get_synonyms(self,identifier):
        s = self.uniprot_2_something(identifier,'STRING')
        s += self.uniprot_2_something(identifier,'neXtProt')
        # Would really like to get MINT and PR here also, but this interface doesn't handle them :<
        return set(s)
