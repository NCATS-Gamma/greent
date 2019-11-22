##################
# This annotator will be used for all nodes regardless of thier type 
# Things like literary synonymization (collecting different names for node)
# adding names 
# or anything we'd like to apply in the general sense.
################

from greent.annotators.annotator import Annotator
from builder.question import LabeledID
import asyncio
from greent.util import Text, LoggingUtil
import logging
import traceback


logger = LoggingUtil.init_logging(__name__, level=logging.DEBUG, format='medium')

class GenericAnnotator(Annotator):
    """
    Singleton class to perform our generic annotation tasks.
    """
    instance = None

    def __init__(self, rosetta):
        if not self.instance:
            self.instance = GenericAnnotator.__GenericAnnotator(rosetta)
    def __getattr__(self, name):
        return getattr(self.instance, name)

    def annotate(self, node):
        # Overriding this method with the generic way 
        self.instance.annotate(node)
    
    class __GenericAnnotator(Annotator):
        def __init__(self, rosetta):
            super().__init__(rosetta)
            self.onto_url = rosetta.core.onto.url
            self.concepts = rosetta.type_graph.concept_model

        def annotate(self, node):     
            ## override this and and other steps here aswell. For now we just grab literary synonyms
            self.get_literary_synonyms(node)
            self.get_good_name(node)
            
        def get_literary_synonyms(self, node):
            #synonym curies 
            synonym_curies = list(map(lambda x : x.identifier if isinstance(x, LabeledID) else x , node.synonyms))
            syns = self.event_loop.run_until_complete(self.fetch_literary_syns(synonym_curies))
            node.properties.update({
                'synonyms': syns
            })
        def get_good_name(self, node):
            logger.debug(f'getting good name for node: {node} ({node.name})')            
            key = f"node_name({node.id})"
            cached_name = self.rosetta.cache.get(key)
            if not cached_name or cached_name == '':
                self.event_loop.run_until_complete(self.set_name(node))

            if node.name != '' :
                #set if name is not empty 
                self.rosetta.cache.set(key,node.name)
                cached_name = node.name

            logger.debug(f'got good name: {node}({node.name})')

        async def resolve_name_by_curie(self, node_curie):
            url = f'{self.onto_url}/label/{node_curie}'
            label = ''
            try:
                response = await self.async_get_json(url)
                label = response['label']
            except Exception as e:
                logger.error(f'Exception {e} raised calling {url}' )
            return {node_curie: label} 
        
        async def set_name(self, node):
            synonym_curies = list(map(lambda x : x.identifier if isinstance(x, LabeledID) else x , node.synonyms))
            # first thing if we can get it using the node's selected Id we don't really worry much
            # but this assumes that the proper ID was selected prior to this, 
            tasks = list(map(lambda synonym: self.resolve_name_by_curie(synonym), synonym_curies))
            results = await asyncio.gather(*tasks, return_exceptions= False)
            #merge the results back to dict
            merged_results ={}
            for x in results:
                for k in x:
                    if x[k] != '':
                        merged_results[k] = x[k]
            results = merged_results
              
            # if we can find a name on the id itself we are good
            if node.id in merged_results:
                node.name = merged_results[node.id]
                return 
            ### Here we select the best name            
            ### reduce the labels in bags of prefixes
            
            prefix_label_bag = {}
            for curie in results:
                curie_prefix = Text.get_curie(curie)
                label = results[curie]
                if curie_prefix not in prefix_label_bag:
                    # this could have been an array, but say we have 
                    prefix_label_bag[curie_prefix] = label                
            ### now go through the list select the first we find
            type_curies = self.concepts.get(node.type).id_prefixes         
            for prefix in type_curies:
                if prefix in prefix_label_bag:
                    node.name = prefix_label_bag[prefix]
            return

        async def fetch_literary_syns(self,synonym_curies):
            tasks = []
            for curie in synonym_curies:
                tasks.append(self.get_syns_from_cache(curie))
            results = await asyncio.gather(*tasks, return_exceptions= False)
            response = []
            for r in filter(lambda x: x and len(x), results):
                desc = map(lambda x: x['desc'], r)
                for name in desc:
                    if name not in response:
                        response.append(name)               
            return response

        async def get_syns_from_cache(self, curie):
            key = f"literal_synonyms({curie})"
            logger.debug(f"[x] Get literal synonyms for {curie}")
            cached = self.rosetta.cache.get(key)
            if cached == None:
                logger.info(f" cache miss: {key}")
                response = await self.async_get_json(f'{self.onto_url}/synonyms/{curie}')
                logger.debug(response)
                self.rosetta.cache.set(key, response)
                return response
            else :
                logger.debug(f"cache hit: {key} ")
                return cached