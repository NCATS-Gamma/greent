import json
from greent.cachedservice import CachedService
from greent.util import LoggingUtil
from greent.graph_components import KNode, KEdge, LabeledID


logger = LoggingUtil.init_logging(__name__)

class Onto(CachedService):
    """ An abstraction for generic questions about ontologies. """
    def __init__(self, name, context):
        super(Onto,self).__init__(name, context)
        self.name = name
    def get_ids(self):
        obj = self.get(f"{self.url}/id_list/{self.name.upper()}")
        return obj
    def is_a(self,identifier,candidate_ancestor):
        obj = self.get(f"{self.url}/is_a/{identifier}/{candidate_ancestor}")
        if obj is None:
            return False
        #print (f"obj: {json.dumps(obj, indent=2)}")
        return obj is not None and 'is_a' in obj and obj['is_a']
    def get_label(self,identifier):
        """ Get the label for an identifier. """
        obj = self.get(f"{self.url}/label/{identifier}")
        return obj['label'] if obj and 'label' in obj else None
    def search(self,name,is_regex=False, full=False):
        """ Search ontologies for a term. """
        obj = self.get(f"{self.url}/search/{name}/?regex={'true' if is_regex else 'false'}")
        results = []
        if full:
            results = obj['values'] if 'values' in obj else []
        else:
            results = [ v['id'] for v in obj['values'] ] if obj and 'values' in obj else []
        return results
    def get_xrefs(self,identifier, filter=None):
        """ Get external references. Optionally filter results. """
        obj = self.get(f"{self.url}/xrefs/{identifier}")
        result = []
        if 'xrefs' in obj:
            for xref in obj['xrefs']:
                if filter:
                    for f in filter:
                        if 'id' in xref:
                            if xref['id'].startswith(f):
                                result.append (xref['id'])
                else:
                    result.append (xref)
        return result
    def get_exact_matches(self,identifier):
        """ Get exact matches.  Seems to be mostly a MONDO thing """
        obj = self.get(f"{self.url}/exactMatch/{identifier}")
        result = []
        if 'exact matches' in obj:
            result.extend(obj['exact matches'])
        return result
    def get_synonyms(self,identifier,curie_pattern=None):
        return self.get(f"{self.url}/synonyms/{identifier}")
    def lookup(self,identifier):
        obj = self.get(f"{self.url}/lookup/{identifier}")
        if obj == None : logger.warning(f'Error: {self.url}/lookup/{identifier} returned {None} ')
        return [ ref["id"] for ref in obj['refs'] ] if obj and 'refs' in obj else []

    def get_anscestors(self, identifier):
        return self.get(f"{self.url}/superterms/{identifier}")
    
    def get_parents(self, identifier):
        return self.get(f"{self.url}/parents/{identifier}")['parents']

    def get_children(self, identifier):
        return self.get(f"{self.url}/children/{identifier}")

        
    def get_ontological_subclass(self, node):
        #Ideally our ancestory list would be same as our query node
        for parent_curie, lbl in node.synonyms:
            response = self.get_children(parent_curie)
            results = []
            predicate = LabeledID(identifier="rdfs:subClassOf", label="is_a")        
            for curie in response:
                name = self.get_label(curie)
                new_node = KNode(curie, type = node.type, name = name)                        
                results.append((
                    self.create_edge(
                        new_node,
                        node,
                        'onto.get_onthological_children',
                        node.id,
                        predicate), new_node))
        return results