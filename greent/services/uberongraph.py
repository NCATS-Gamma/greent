from string import Template
import json
import os
import logging
from greent.service import Service
from greent.triplestore import TripleStore
from greent.util import LoggingUtil
from greent.util import Text
from greent.graph_components import KEdge, KNode, LabeledID
from greent import node_types
from pprint import pprint
from datetime import datetime as dt
import datetime
import inspect

logger = LoggingUtil.init_logging(__name__)

class UberonGraphKS(Service):
    """A knowledge source created by 1) Combining cell ontology, uberon, and
    HPO, 2) Reasoning over the total graph to realize many implicit edges.
    Created by Jim Balhoff"""

    def __init__(self, context): #triplestore):
        super(UberonGraphKS, self).__init__("uberongraph", context)
        self.triplestore = TripleStore (self.url)
        #TODO: Pull this from the biolink model?
        self.class_defs = { node_types.CELL: 'CL:0000000',
                            node_types.ANATOMICAL_ENTITY: 'UBERON:0001062',
                            node_types.BIOLOGICAL_PROCESS: 'GO:0008150',
                            node_types.MOLECULAR_ACTIVITY: 'GO:0003674',
                            node_types.CHEMICAL_SUBSTANCE: 'CHEBI:24431',
                            node_types.DISEASE: 'MONDO:0000001',
                            node_types.PHENOTYPIC_FEATURE: 'UPHENO:0001002'}

    def query_uberongraph (self, query):
        """ Execute and return the result of a SPARQL query. """
        return self.triplestore.execute_query (query)

    def get_edges(self,source_type,obj_type):
        """Given an UBERON id, find other UBERONS that are parts of the query"""
        text="""
        prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        prefix UBERON: <http://purl.obolibrary.org/obo/UBERON_>
        prefix CL: <http://purl.obolibrary.org/obo/CL_>
        prefix GO: <http://purl.obolibrary.org/obo/GO_>
        prefix CHEBI: <http://purl.obolibrary.org/obo/CHEBI_>
        prefix MONDO: <http://purl.obolibrary.org/obo/MONDO_>
        prefix UPHENO: <http://purl.obolibrary.org/obo/UPHENO_>
        prefix BFO: <http://purl.obolibrary.org/obo/BFO_>
        select distinct ?p ?pLabel
        from <http://reasoner.renci.org/ontology>
        where {
            graph <http://reasoner.renci.org/redundant> {
                ?sourceID ?p ?objID .
            }
            graph <http://reasoner.renci.org/ontology/closure> {
                ?sourceID rdfs:subClassOf $sourcedefclass .
            }
            graph <http://reasoner.renci.org/ontology/closure> {
                ?objID rdfs:subClassOf $objdefclass .
                hint:Prior hint:runFirst true .
            }
            ?p rdfs:label ?pLabel .
        }
        """
        results = self.triplestore.query_template(
            inputs  = { 'sourcedefclass': self.class_defs[source_type], 'objdefclass': self.class_defs[obj_type] }, \
            outputs = [ 'p', 'pLabel' ], \
            template_text = text \
        )
        return results

    def get_label (self, identifier):
        obo_id = Text.curie_to_obo(identifier)
        text = """
        prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        select distinct ?label
        from <http://reasoner.renci.org/ontology>
        where {
            $obo_id rdfs:label ?label .
        }
        """
        results = self.triplestore.query_template(
                inputs= {'obo_id': obo_id}, outputs = ['label'], template_text=text)
        if len(results) < 1:
            return ''
        return results[0]['label']

    def cell_get_cellname (self, cell_identifier):
        """ Identify label for a cell type
        :param cell: CL identifier for cell type 
        """
        text = """
        prefix CL: <http://purl.obolibrary.org/obo/CL_>
        select distinct ?cellLabel
        from <http://reasoner.renci.org/nonredundant>
        from <http://reasoner.renci.org/ontology>
        where {
                  $cellID rdfs:label ?cellLabel .
              }
        """
        results = self.triplestore.query_template( 
            inputs = { 'cellID': cell_identifier }, \
            outputs = [ 'cellLabel' ], \
            template_text = text \
        )
        return results


    def get_anatomy_parts(self, anatomy_identifier):
        """Given an UBERON id, find other UBERONS that are parts of the query"""
        anatomy_identifier = f"<{anatomy_identifier}>"
        text="""
        prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        prefix UBERON: <http://purl.obolibrary.org/obo/UBERON_>
        prefix BFO: <http://purl.obolibrary.org/obo/BFO_>
        select distinct ?part ?partlabel
        from <http://reasoner.renci.org/nonredundant> 
        from <http://reasoner.renci.org/ontology>
        where {
                $anatomy_id BFO:0000051 ?part .
                graph <http://reasoner.renci.org/ontology/closure> {
                  ?part rdfs:subClassOf UBERON:0001062 .
                }
                ?part rdfs:label ?partlabel .
        }
        """
        results = self.triplestore.query_template(  
            inputs  = { 'anatomy_id': anatomy_identifier }, \
            outputs = [ 'part', 'partlabel' ], \
            template_text = text \
        )
        for result in results:
            result['curie'] = Text.obo_to_curie(result['part'])
        return results

    def get_neighbor(self,input_id,output_type,subject=True):
        parents = {node_types.ANATOMICAL_ENTITY:"<http://purl.obolibrary.org/obo/UBERON_0001062>",
                   node_types.DISEASE: "<http://purl.obolibrary.org/obo/MONDO_0000001>",
                   node_types.MOLECULAR_ACTIVITY: "<http://purl.obolibrary.org/obo/GO_0003674>",
                   node_types.BIOLOGICAL_PROCESS: "<http://purl.obolibrary.org/obo/GO_0008150>",
                   node_types.CHEMICAL_SUBSTANCE: "<http://purl.obolibrary.org/obo/CHEBI_24431>",
                   node_types.PHENOTYPIC_FEATURE: "<http://purl.obolibrary.org/obo/HP_0000118>"}
        pref=Text.get_curie(input_id)
        obo_prefix = f'PREFIX {pref}: <http://purl.obolibrary.org/obo/{pref}_>' 
        text="""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        """+obo_prefix+"""
        select distinct ?output_id ?output_label ?p ?pLabel 
        from <http://reasoner.renci.org/nonredundant>
        from <http://reasoner.renci.org/ontology>
        where {
            graph <http://reasoner.renci.org/redundant> {
        """
        if subject:
            text+='	 $input_id ?p ?output_id .'
        else:
            text+='  ?output_id ?p $input_id .'
        text += """
            }
            graph <http://reasoner.renci.org/ontology/closure> {
                ?output_id rdfs:subClassOf $parent .
            }
            ?output_id rdfs:label ?output_label .
  			?p rdfs:label ?pLabel .
        }
        """
        results = self.triplestore.query_template(
            inputs = { 'input_id': input_id, 'parent': parents[output_type] },
            outputs = [ 'output_id', 'output_label', 'p', 'pLabel' ],
            template_text = text
        )
        return results


    def anatomy_to_anatomy(self, identifier):
        results = {'subject': [], 'object': []}
        for direction,query in \
            (('subject','      ?input_id ?p ?output_id .'),
             ('object','       ?output_id ?p ?input_id .')):
            text=""" PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            prefix UBERON: <http://purl.obolibrary.org/obo/UBERON_>
            select distinct ?output_id ?output_label ?p ?pLabel 
            from <http://reasoner.renci.org/nonredundant>
            from <http://reasoner.renci.org/ontology>
            where {
                graph <http://reasoner.renci.org/redundant> {
            """ + query + \
            """
                }
                graph <http://reasoner.renci.org/ontology/closure> {
                    ?output_id rdfs:subClassOf UBERON:0001062 . 
                }
                ?output_id rdfs:label ?output_label .
                ?p rdfs:label ?pLabel .
            }
            """
            results[direction] += self.triplestore.query_template(
                inputs = { 'input_id': identifier },
                outputs = [ 'output_id', 'output_label', 'p', 'pLabel' ],
                template_text = text
            )
        return results


    def anatomy_to_go (self, anatomy_identifier):
        """ Identify process and functions related to anatomical terms (anatomy, cell, components).

        """
        #This is a bit messy, but we need to do 4 things.  We are looking for go terms
        # that are either biological processes or activities and we are looking for predicates
        # that point either direction.
        results = {'subject': [], 'object': []}
        for goParent in ('GO:0008150','GO:0003674'):
            for direction,query in(('subject','      $anatID ?p ?goID'),('object','        ?goID ?p $anatID')):
                text = """
                prefix GO: <http://purl.obolibrary.org/obo/GO_>
                select distinct ?goID ?goLabel ?p ?pLabel
                from <http://reasoner.renci.org/nonredundant>
                from <http://reasoner.renci.org/ontology>
                where {
                    graph <http://reasoner.renci.org/redundant> {
                """+ query + """
                    }
                    graph <http://reasoner.renci.org/ontology/closure> {
                        ?goID rdfs:subClassOf $goParent .
                    }
                    ?goID rdfs:label ?goLabel .
                    ?p rdfs:label ?pLabel
                }
                """
                results[direction] += self.triplestore.query_template(
                    inputs = { 'anatID': anatomy_identifier, 'goParent': goParent }, \
                    outputs = [ 'goID', 'goLabel', 'p', 'pLabel' ], \
                    template_text = text \
                )
        return results

    def go_to_anatomy (self, input_identifier):
        """ Identify anatomy terms related to process/functions.

        :param input_identifier: identifier for anatomy (including cell and cellular component)
        """
        # we are looking for predicates that point either direction.
        results = {'subject': [], 'object': []}
        for direction,query in(('subject','      ?anatID ?p $goID'),('object','        $goID ?p ?anatID')):
            text = """
            prefix UBERON: <http://purl.obolibrary.org/obo/UBERON_>
            prefix GO: <http://purl.obolibrary.org/obo/GO_>
            select distinct ?anatID ?anatLabel ?p ?pLabel
            from <http://reasoner.renci.org/nonredundant>
            from <http://reasoner.renci.org/ontology>
            where {
                graph <http://reasoner.renci.org/redundant> {
            """+ query + """
                }
                graph <http://reasoner.renci.org/ontology/closure> {
                    ?anatID rdfs:subClassOf UBERON:0001062 .
                }
                ?anatID rdfs:label ?anatLabel .
                ?p rdfs:label ?pLabel
            }
            """
            results[direction] += self.triplestore.query_template(
                inputs = { 'goID': input_identifier },
                outputs = [ 'anatID', 'anatLabel', 'p', 'pLabel' ],
                template_text = text
            )
        return results

    def pheno_or_disease_to_go(self, identifier):
        text="""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        prefix BFO: <http://purl.obolibrary.org/obo/BFO_>
        prefix GO: <http://purl.obolibrary.org/obo/GO_>
        prefix MONDO: <http://purl.obolibrary.org/obo/MONDO_>
        prefix HP: <http://purl.obolibrary.org/obo/MONDO_>
        select distinct ?goID ?goLabel ?p ?pLabel 
        from <http://reasoner.renci.org/nonredundant>
        from <http://reasoner.renci.org/ontology>
        where {
            graph <http://reasoner.renci.org/redundant> {
    			$input_id ?p ?goID .
            }
            graph <http://reasoner.renci.org/ontology/closure> {
                { ?goID rdfs:subClassOf GO:0008150 . }
                UNION
                { ?goID rdfs:subClassOf GO:0003674 . }
            }
            ?goID rdfs:label ?goLabel .
  			?p rdfs:label ?pLabel .
        }
        """
        results = self.triplestore.query_template(
            inputs = { 'input_id': identifier },
            outputs = [ 'goID', 'goLabel', 'p', 'pLabel' ],
            template_text = text
        )
        return results

    def phenotype_to_anatomy (self, hp_identifier):
        """ Identify anatomies related to phenotypes.

        :param cell: HP identifier for phenotype
        """

        #The subclassof uberon:0001062 ensures that the result
        #is an anatomical entity.
        #We don't need to do the subject/object game because there's nothing in ubergraph
        # that goes that direction
        text = """
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX UBERON: <http://purl.obolibrary.org/obo/UBERON_>
            SELECT DISTINCT ?anatomy_id ?anatomy_label ?predicate ?predicate_label             
            FROM <http://reasoner.renci.org/ontology>
            WHERE {
                graph <http://reasoner.renci.org/redundant>{
                    $HPID ?predicate ?anatomy_id.
                }                
                graph <http://reasoner.renci.org/ontology/closure>{
                    ?anatomy_id rdfs:subClassOf UBERON:0001062.
                }
                ?anatomy_id rdfs:label ?anatomy_label .
                OPTIONAL {?predicate rdfs:label ?predicate_label.}
            }
        """
        results = self.triplestore.query_template( 
            inputs = { 'HPID': hp_identifier }, \
            outputs = [ 'anatomy_id', 'anatomy_label', 'predicate', 'predicate_label'],\
            template_text = text \
        )
        return results

    def anatomy_to_phenotype(self, uberon_id):
        #sparql very identical to phenotype_to_anatomy. could not find any anatomical 
        # entity that is a subject of subclass of HP:0000118, in ubergraph at this point. 
        # treating this as another version of pheno -> anatomical_entity but when 
        # anatomical_entity is known an
        # we want to go back to  a phenotype. 
        text="""
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX HP:<http://purl.obolibrary.org/obo/HP_>
            SELECT DISTINCT ?pheno_id ?pheno_label ?predicate ?predicate_label 
            FROM <http://reasoner.renci.org/ontology>
            WHERE {
                graph <http://reasoner.renci.org/redundant> {
                    ?pheno_id ?predicate $UBERONID.
                }                
                graph <http://reasoner.renci.org/ontology/closure>{
                    ?pheno_id rdfs:subClassOf HP:0000118.
                }
                ?pheno_id rdfs:label ?pheno_label.
                OPTIONAL {?predicate rdfs:label ?predicate_label.}
            }"""  
        results = self.triplestore.query_template(
            inputs = { 'UBERONID': uberon_id }, \
            outputs = [ 'pheno_id', 'pheno_label', 'predicate', 'predicate_label' ],\
            template_text = text \
        )
        return results

    def biological_process_or_activity_to_chemical(self, go_id):
        """
        Given a chemical finds associated GO Molecular Activities.
        """
        results = []
     
        text = """
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX GO:  <http://purl.obolibrary.org/obo/GO_>
            PREFIX RO: <http://purl.obolibrary.org/obo/RO_>
            PREFIX chemical_entity: <http://purl.obolibrary.org/obo/CHEBI_24431>
            PREFIX chemical_class: <http://purl.obolibrary.org/obo/CHEBI_24431>
            SELECT DISTINCT ?chebi_id ?predicate ?label_predicate ?chebi_label
            from <http://reasoner.renci.org/ontology>
            from <http://reasoner.renci.org/nonredundant>
            where {
            $GO_ID ?predicate ?chebi_id. 
            ?chebi_id rdfs:label ?chebi_label.
            GRAPH <http://reasoner.renci.org/ontology/closure>
  	            { ?chebi_id rdfs:subClassOf chemical_class:.} 
            ?predicate rdfs:label ?label_predicate.
            FILTER ( datatype(?label_predicate) = xsd:string) 
            }
        """ 
        results = self.triplestore.query_template(
            template_text = text,
            outputs = ['chebi_id', 'predicate','label_predicate', 'chebi_label'],
            inputs = {'GO_ID': go_id})
        return results

    def pheno_to_biological_activity(self, pheno_id):
        """
        Finds biological activities related to a phenotype
        :param :pheno_id phenotype identifier
        """
        text = """
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX owl: <http://www.w3.org/2002/07/owl#>
            PREFIX GO: <http://purl.obolibrary.org/obo/GO_>
            PREFIX has_phenotype_affecting: <http://purl.obolibrary.org/obo/UPHENO_0000001>
            PREFIX RO: <http://purl.obolibrary.org/obo/RO_>
            prefix HP: <http://purl.obolibrary.org/obo/HP_>

            SELECT DISTINCT ?go_id ?predicate ?predicate_label ?go_label
            from <http://reasoner.renci.org/nonredundant>
            from <http://reasoner.renci.org/ontology>
            WHERE {
            $pheno_type ?predicate  ?go_id.
            ?go_id rdfs:label ?go_label.
            graph <http://reasoner.renci.org/ontology/closure> {
                { ?go_id rdfs:subClassOf GO:0008150 . }
                UNION
                { ?go_id rdfs:subClassOf GO:0003674 . }
            }
            ?predicate rdfs:label ?predicate_label.
            }
        """
        results = self.triplestore.query_template(
            template_text = text,
            inputs = {'pheno_type': pheno_id},
            outputs = ['go_id', 'predicate', 'predicate_label', 'go_label']
        )
        return results

    def disease_to_anatomy(self, disease_id):
        #THere are no anatomy-(predicate)->disease triples
        text = """
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX anatomicalEntity: <http://purl.obolibrary.org/obo/UBERON_0001062>
            SELECT DISTINCT ?anatomyID ?predicate ?predicate_label ?anatomy_label
            FROM <http://reasoner.renci.org/nonredundant>
            FROM <http://reasoner.renci.org/ontology>
            WHERE {
            graph <http://reasoner.renci.org/redundant> {
                $diseaseID ?predicate ?anatomyID.
            }
            ?anatomyID rdfs:label ?anatomy_label.
            graph <http://reasoner.renci.org/ontology/closure> {
                ?anatomyID rdfs:subClassOf anatomicalEntity: .
            }
            ?predicate rdfs:label ?predicate_label.
            }
        """
        results = []
        results = self.triplestore.query_template(
            template_text = text,
            outputs = ['anatomyID', 'predicate', 'predicate_label', 'anatomy_label'],
            inputs = {'diseaseID': disease_id}
        )
        return results

    def anatomy_to_chemical_substance(self, anatomy_id):
        #There's no chemical-(predicate)->anatomy
        text = """
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX chemical_entity: <http://purl.obolibrary.org/obo/CHEBI_24431>
        SELECT DISTINCT ?predicate ?predicate_label ?chemical_entity ?chemical_label
        FROM <http://reasoner.renci.org/ontology>
        FROM <http://reasoner.renci.org/redundant>
        WHERE {
            $anatomy_id ?predicate ?chemical_entity.
            graph <http://reasoner.renci.org/ontology/closure> 
            {
                ?chemical_entity rdfs:subClassOf chemical_entity:.
            }
            ?predicate rdfs:label ?predicate_label .
            ?chemical_entity rdfs:label ?chemical_label.
        }
        """
        results = []
        results = self.triplestore.query_template(
            template_text = text,
            outputs = ['predicate','predicate_label','chemical_entity', 'chemical_label'],
            inputs = {'anatomy_id': anatomy_id}
        )
        return results

    def anatomy_to_disease(self, anatomy_id):
        text = """
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX disease: <http://purl.obolibrary.org/obo/MONDO_0000001>
        SELECT DISTINCT  ?predicate ?predicate_label ?disease ?disease_label
        FROM <http://reasoner.renci.org/ontology>
        FROM <http://reasoner.renci.org/redundant>{
        ?disease ?predicate $anatomy_id.
        graph <http://reasoner.renci.org/ontology/closure> 
        {
            ?disease rdfs:subClassOf disease:.
        }
        ?predicate rdfs:label ?predicate_label .
        ?disease rdfs:label ?disease_label.
        }
        """
        results = []
        results = self.triplestore.query_template(
            template_text = text,
            outputs = ['predicate','predicate_label','disease', 'disease_label'],
            inputs = {'anatomy_id': anatomy_id}
        )
        return results


    def create_phenotype_anatomy_edge(self, node_id, node_label, input_id ,phenotype_node):
        predicate = LabeledID(identifier='GAMMA:0000002', label='inverse of has phenotype affecting')
        anatomy_node = KNode ( Text.obo_to_curie(node_id), type=node_types.ANATOMICAL_ENTITY , name=node_label)
        edge = self.create_edge(anatomy_node, phenotype_node,'uberongraph.get_anatomy_by_phenotype_graph', input_id, predicate)
        #node.name = node_label
        return edge,anatomy_node

    def create_anatomy_phenotype_edge(self, node_id, node_label, input_id ,anatomy_node):
        predicate = LabeledID(identifier='GAMMA:0000002', label='inverse of has phenotype affecting')
        phenotype_node = KNode ( Text.obo_to_curie(node_id), type=node_types.PHENOTYPIC_FEATURE , name=node_label)
        edge = self.create_edge(anatomy_node, phenotype_node,'uberongraph.get_phenotype_by_anatomy_graph', input_id, predicate)
        #node.name = node_label
        return edge,phenotype_node

    def dep_get_anatomy_by_phenotype_graph (self, phenotype_node):
        results = []
        for curie in phenotype_node.get_synonyms_by_prefix('HP'):
            anatomies = self.phenotype_to_anatomy (curie)
            for r in anatomies:
                node = KNode(r['anatomy_id'], type=node_types.ANATOMICAL_ENTITY, name= r['anatomy_label'])
                # try to derive the label from the relation for the new ubergraph axioms 
                predicate_label = r['predicate_label'] or '_'.join(r['predicate'].split('#')[-1].split('.'))
                predicate = LabeledID(Text.obo_to_curie(r['predicate']), predicate_label)
                edge = self.create_edge(
                    phenotype_node,
                    node,
                    'uberongraph.get_anatomy_by_phenotype_graph',
                    phenotype_node.id,
                    predicate
                )
                # edge, node = self.create_phenotype_anatomy_edge(r['anatomy_id'],r['anatomy_label'],curie,phenotype_node)
                if phenotype_node.name is None:
                    phenotype_node.name = r['input_label']
                results.append ( (edge, node) )
                #These tend to be very high level terms.  Let's also get their parts to
                #be more inclusive.
                #TODO: there ought to be a more principled way to take care of this, but
                #it highlights the uneasy relationship between the high level world of
                #smartapi and the low-level sparql-vision.
                part_results = self.get_anatomy_parts( r['anatomy_id'] )
                for pr in part_results:
                    # pedge, pnode = self.create_phenotype_anatomy_edge(pr['part'],pr['partlabel'],curie,phenotype_node)
                    pnode = KNode(pr['part'], type= node_types.ANATOMICAL_ENTITY, name= pr['partlabel'])
                    pedge = self.create_edge(
                        phenotype_node,
                        pnode,
                        'uberongraph.get_anatomy_by_phenotype_graph',
                        phenotype_node.id,
                        predicate
                    )
                    results.append ( (pedge, pnode) )
        return results

    def get_out_by_in(self,input_node,output_type,prefixes,subject=True,object=True):
        returnresults = []
        caller=f'uberongraph.{inspect.stack()[1][3]}'
        results = {'subject': [], 'object': []}
        curies = set()
        for pre in prefixes:
            curies.update( input_node.get_synonyms_by_prefix(pre) )
        for curie in curies:
            results['subject'] += self.get_neighbor(curie,output_type,subject=True)
            results['object'] += self.get_neighbor(curie,output_type,subject=False)
        for direction in ['subject','object']:
            done = set()
            for r in results[direction]:
                key = (r['p'],r['output_id'])
                if key in done:
                    continue
                predicate = LabeledID(Text.obo_to_curie(r['p']),r['pLabel'])
                output_node = KNode(r['output_id'],type=output_type,name=r['output_label'])
                if direction == 'subject':
                    edge = self.create_edge(input_node, output_node, caller, curie, predicate)
                else:
                    edge = self.create_edge(output_node, input_node, caller , curie, predicate)
                done.add(key)
                returnresults.append((edge,output_node))
        return returnresults

    #Don't get confused.  There is the direction of the statement (who is the subject
    # and who is the object) and which of them we are querying by.  We want to query
    # independent of direction i.e. let the input node be either the subject or the object.

    def get_anatomy_by_anatomy_graph(self, anatomy_node):
        return self.get_out_by_in(anatomy_node,node_types.ANATOMICAL_ENTITY,['UBERON','CL','GO'])

    def get_phenotype_by_anatomy_graph (self, anatomy_node):
        return self.get_out_by_in(anatomy_node,node_types.PHENOTYPIC_FEATURE,['UBERON','CL','GO'])

    def get_chemical_substance_by_anatomy(self, anatomy_node):
        return self.get_out_by_in(anatomy_node,node_types.CHEMICAL_SUBSTANCE,['UBERON','CL','GO'])

    def get_process_by_anatomy(self, anatomy_node):
        return self.get_out_by_in(anatomy_node,node_types.BIOLOGICAL_PROCESS,['UBERON','CL','GO'])

    def get_activity_by_anatomy(self, anatomy_node):
        return self.get_out_by_in(anatomy_node,node_types.MOLECULAR_ACTIVITY,['UBERON','CL','GO'])

    def get_disease_by_anatomy_graph(self, anatomy_node):
        return self.get_out_by_in(anatomy_node,node_types.DISEASE,['UBERON','CL','GO'])

    def get_anatomy_by_process_or_activity(self, go_node):
        return self.get_out_by_in(go_node,node_types.ANATOMICAL_ENTITY,['GO'])

    def get_chemical_entity_by_process_or_activity(self, go_node):
        return self.get_out_by_in(go_node,node_types.CHEMICAL_SUBSTANCE,['GO'])

    def get_process_by_disease(self, disease_node):
        return self.get_out_by_in(disease_node,node_types.BIOLOGICAL_PROCESS,['MONDO'])

    def get_activity_by_disease(self,disease_node):
        return self.get_out_by_in(disease_node,node_types.MOLECULAR_ACTIVITY,['MONDO'])

    def get_anatomy_by_disease(self,disease_node):
        return self.get_out_by_in(disease_node,node_types.ANATOMICAL_ENTITY,['MONDO'])

    def get_chemical_by_disease(self, disease_node):
        return self.get_out_by_in(disease_node,node_types.CHEMICAL_SUBSTANCE,['MONDO'])

    def get_process_by_phenotype(self, pheno_node):
        return self.get_out_by_in(pheno_node,node_types.BIOLOGICAL_PROCESS,['HP'])

    def get_chemical_by_phenotype(self, pheno_node):
        return self.get_out_by_in(pheno_node,node_types.CHEMICAL_SUBSTANCE,['HP'])

    def get_activity_by_phenotype(self, pheno_node):
        return self.get_out_by_in(pheno_node,node_types.MOLECULAR_ACTIVITY,['HP'])

    def get_anatomy_by_phenotype_graph (self, pheno_node):
        return self.get_out_by_in(pheno_node,node_types.ANATOMICAL_ENTITY,['HP'])

    def get_chemical_by_chemical (self, chem_node):
        return self.get_out_by_in(chem_node,node_types.CHEMICAL_SUBSTANCE,['CHEBI'])
