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
        if anatomy_identifier.startswith('http'):
            anatomy_identifier = Text.obo_to_curie(anatomy_identifier)
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


    def anatomy_to_cell (self, anatomy_identifier):
        """ Identify anatomy terms related to cells.

        :param cell: CL identifier for cell type
        """
        text = """
        prefix UBERON: <http://purl.obolibrary.org/obo/UBERON_>
        prefix CL: <http://purl.obolibrary.org/obo/CL_>
        prefix BFO: <http://purl.obolibrary.org/obo/BFO_>
        select distinct ?cellID ?cellLabel
        from <http://reasoner.renci.org/nonredundant>
        from <http://reasoner.renci.org/ontology>
        where {
            graph <http://reasoner.renci.org/redundant> {
                ?cellID BFO:0000050 $anatomyID .
            }
            graph <http://reasoner.renci.org/ontology/closure> {
                ?cellID rdfs:subClassOf CL:0000000 .
            }
            ?cellID rdfs:label ?cellLabel .
        }

        """
        results = self.triplestore.query_template(
            inputs = { 'anatomyID': anatomy_identifier }, \
            outputs = [ 'cellID', 'cellLabel' ], \
            template_text = text \
        )
        return results


    def cell_to_anatomy (self, cell_identifier):
        """ Identify anatomy terms related to cells.

        :param cell: CL identifier for cell type 
        """
        text = """
        prefix CL: <http://purl.obolibrary.org/obo/CL_>
        prefix BFO: <http://purl.obolibrary.org/obo/BFO_>
        prefix UBERON: <http://purl.obolibrary.org/obo/UBERON_>
        select distinct ?anatomyID ?anatomyLabel
        from <http://reasoner.renci.org/nonredundant>
        from <http://reasoner.renci.org/ontology>
        where {
            graph <http://reasoner.renci.org/redundant> {
                $cellID BFO:0000050 ?anatomyID .
            }
            graph <http://reasoner.renci.org/ontology/closure> {
                ?anatomyID rdfs:subClassOf UBERON:0001062 .
            }
            ?anatomyID rdfs:label ?anatomyLabel .
        }
        """
        results = self.triplestore.query_template( 
            inputs = { 'cellID': cell_identifier }, \
            outputs = [ 'anatomyID', 'anatomyLabel' ], \
            template_text = text \
        )
        return results

    def cell_to_go (self, cell_identifier):
        """ Identify anatomy terms related to cells.

        :param cell: CL identifier for cell type
        """
        #This is a bit messy, but we need to do 4 things.  We are looking for go terms
        # that are either biological processes or activities and we are looking for predicates
        # that point either direction.
        results = {'subject': [], 'object': []}
        for goParent in ('GO:0008150','GO:0003674'):
            for direction,query in(('subject','      $cellID ?p ?goID'),('object','        ?goID ?p $cellID')):
                text = """
                prefix CL: <http://purl.obolibrary.org/obo/CL_>
                prefix BFO: <http://purl.obolibrary.org/obo/BFO_>
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
                    inputs = { 'cellID': cell_identifier, 'goParent': goParent }, \
                    outputs = [ 'goID', 'goLabel', 'p', 'pLabel' ], \
                    template_text = text \
                )
        return results

    def go_to_cell (self, input_identifier):
        """ Identify anatomy terms related to cells.

        :param cell: CL identifier for cell type
        """
        # we are looking for predicates that point either direction.
        results = {'subject': [], 'object': []}
        for direction,query in(('subject','      ?cellID ?p $goID'),('object','        $goID ?p ?cellID')):
            text = """
            prefix CL: <http://purl.obolibrary.org/obo/CL_>
            prefix BFO: <http://purl.obolibrary.org/obo/BFO_>
            prefix GO: <http://purl.obolibrary.org/obo/GO_>
            select distinct ?cellID ?cellLabel ?p ?pLabel
            from <http://reasoner.renci.org/nonredundant>
            from <http://reasoner.renci.org/ontology>
            where {
                graph <http://reasoner.renci.org/redundant> {
            """+ query + """
                }
                graph <http://reasoner.renci.org/ontology/closure> {
                    ?cellID rdfs:subClassOf CL:0000000 .
                }
                ?cellID rdfs:label ?cellLabel .
                ?p rdfs:label ?pLabel
            }
            """
            results[direction] += self.triplestore.query_template(
                inputs = { 'goID': input_identifier },
                outputs = [ 'cellID', 'cellLabel', 'p', 'pLabel' ],
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
        """ Identify anatomy terms related to cells.

        :param cell: HP identifier for phenotype
        """

        #The subclassof uberon:0001062 ensures that the result
        #is an anatomical entity.
        text = """
        prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        prefix UBERON: <http://purl.obolibrary.org/obo/UBERON_>
        prefix HP: <http://purl.obolibrary.org/obo/HP_>
        prefix part_of: <http://purl.obolibrary.org/obo/BFO_0000050>
        prefix has_part: <http://purl.obolibrary.org/obo/BFO_0000051>
        prefix depends_on: <http://purl.obolibrary.org/obo/RO_0002502>
        prefix phenotype_of: <http://purl.obolibrary.org/obo/UPHENO_0000001>
        select distinct ?anatomy_id ?anatomy_label ?input_label
        from <http://reasoner.renci.org/nonredundant>
        from <http://reasoner.renci.org/ontology>
        where {
                  graph <http://reasoner.renci.org/ontology/closure> {
                    ?anatomy_id rdfs:subClassOf UBERON:0001062 .
                  }
                  ?anatomy_id rdfs:label ?anatomy_label .
                  graph <http://reasoner.renci.org/nonredundant> {
                       ?phenotype phenotype_of: ?anatomy_id .
                  }
                  graph <http://reasoner.renci.org/ontology/closure> {
                    $HPID rdfs:subClassOf ?phenotype .
                  }
                  $HPID rdfs:label ?input_label .
              }
        """
        results = self.triplestore.query_template( 
            inputs = { 'HPID': hp_identifier }, \
            outputs = [ 'anatomy_id', 'anatomy_label', 'input_label'],\
            template_text = text \
        )
        return results

    def anatomy_to_phenotype(self, uberon_id):
        text="""
        prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        prefix UBERON: <http://purl.obolibrary.org/obo/UBERON_>
        prefix HP: <http://purl.obolibrary.org/obo/HP_>
        prefix part_of: <http://purl.obolibrary.org/obo/BFO_0000050>
        prefix has_part: <http://purl.obolibrary.org/obo/BFO_0000051>
        prefix depends_on: <http://purl.obolibrary.org/obo/RO_0002502>
        prefix phenotype_of: <http://purl.obolibrary.org/obo/UPHENO_0000001>
        select distinct ?pheno_id ?anatomy_label ?pheno_label
        from <http://reasoner.renci.org/nonredundant>
        from <http://reasoner.renci.org/ontology>
        where {
                  $UBERONID rdfs:label ?anatomy_label .
                  graph <http://reasoner.renci.org/nonredundant> {
                       ?phenotype phenotype_of: $UBERONID .
                  }
                  graph <http://reasoner.renci.org/ontology/closure> {
                    ?pheno_id rdfs:subClassOf ?phenotype .
                  }
                  ?pheno_id rdfs:label ?pheno_label .
              }
        """
        #The subclassof uberon:0001062 ensures that the result
        #is an anatomical entity.
        results = self.triplestore.query_template(
            inputs = { 'UBERONID': uberon_id }, \
            outputs = [ 'pheno_id', 'anatomy_label', 'pheno_label'],\
            template_text = text \
        )
        return results

    def molecular_function_to_chemical(self, go_id):
        """
        Get relation ship between Chemicals and molecular function in eiether direction."""
        results = []
     
        text = """
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX GO: <http://purl.obolibrary.org/obo/GO_>
            PREFIX CHEBI: <http://purl.obolibrary.org/obo/CHEBI_>
            PREFIX owl: <http://www.w3.org/2002/07/owl#>
            SELECT DISTINCT ?predicate ?label_predicate ?chemical_entity
                from <http://reasoner.renci.org/ontology>
                from <http://reasoner.renci.org/nonredundant>
            where {
                {$GO_ID (owl:equivalentClass|rdfs:subClassOf)* GO:0003674}.
                $GO_ID ?predicate ?chemical_entity. 
                ?predicate rdfs:label ?label_predicate.
                

            }
        """ 
        # every molucular_function ontology from GO
        # with Everything from CHEBI (i.e CHEBI:35293 => chemical entity) , @TODO abandon this if re inserting is fine {?chemical_entity rdfs:subClassOf* CHEBI:35293}.
        results = self.triplestore.query_template(
            template_text = text,
            outputs = ['predicate','label_predicate', 'chemical_entity'],
            inputs = {'GO_ID': go_id})
        return results

    def chemical_to_molecular_function(self, chebi_id):
        text = """
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX GO: <http://purl.obolibrary.org/obo/GO_>
            PREFIX CHEBI: <http://purl.obolibrary.org/obo/CHEBI_>
            PREFIX owl: <http://www.w3.org/2002/07/owl#>
            SELECT DISTINCT ?predicate ?label_predicate ?go_id
                from <http://reasoner.renci.org/ontology>
                from <http://reasoner.renci.org/nonredundant>
            where {
                {$CHEBI_ID (owl:equivalentClass|rdfs:subClassOf)* CHEBI:24431}.
                $CHEBI_ID ?predicate ?go_id. 
                ?predicate rdfs:label ?label_predicate.
                
                }
        """ 
        results = self.triplestore.query_template(
            template_text = text,
            outputs = ['predicate', 'label_predicate', 'go_id'],
            inputs = {'CHEBI_ID': chebi_id}
        )
        return results



    def get_anatomy_by_cell_graph (self, cell_node):
        anatomies = self.cell_to_anatomy (cell_node.id)
        results = []
        predicate = LabeledID(identifier='BFO:0000050', label='part_of')
        for r in anatomies:
            anatomy_node = KNode (Text.obo_to_curie(r['anatomyID']), type=node_types.ANATOMICAL_ENTITY, name=r['anatomyLabel'] )
            edge = self.create_edge(cell_node, anatomy_node, 'uberongraph.get_anatomy_by_cell_graph', cell_node.id, predicate)
            results.append ( (edge, anatomy_node) )
        return results

    def get_cell_by_anatomy_graph (self, anatomy_node):
        cells = self.anatomy_to_cell(anatomy_node.id)
        results = []
        predicate = LabeledID(identifier='BFO:0000050', label='part_of')
        for r in cells:
            cell_node = KNode (Text.obo_to_curie(r['cellID']), type=node_types.CELL, name=r['cellLabel'] )
            edge = self.create_edge(cell_node, anatomy_node, 'uberongraph.get_cell_by_anatomy_graph', anatomy_node.id, predicate)
            results.append ( (edge, cell_node) )
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

    def get_anatomy_by_phenotype_graph (self, phenotype_node):
        results = []
        for curie in phenotype_node.get_synonyms_by_prefix('HP'):
            anatomies = self.phenotype_to_anatomy (curie)
            for r in anatomies:
                edge, node = self.create_phenotype_anatomy_edge(r['anatomy_id'],r['anatomy_label'],curie,phenotype_node)
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
                    pedge, pnode = self.create_phenotype_anatomy_edge(pr['part'],pr['partlabel'],curie,phenotype_node)
                    results.append ( (pedge, pnode) )
        return results

    def get_process_or_activity_by_cell(self, cell_node):
        returnresults = []
        for curie in cell_node.get_synonyms_by_prefix('CL'):
            results = self.cell_to_go(curie)
            for direction in ['subject','object']:
                done = set()
                for r in results[direction]:
                    key = (r['p'],r['goID'])
                    if key in done:
                        continue
                    predicate = LabeledID(Text.obo_to_curie(r['p']),r['pLabel'])
                    go_node = KNode(r['goID'],type=node_types.BIOLOGICAL_PROCESS_OR_ACTIVITY,name=r['goLabel'])
                    if direction == 'subject':
                        edge = self.create_edge(cell_node, go_node, 'uberongraph.get_process_or_activity_by_cell', curie, predicate)
                    else:
                        edge = self.create_edge(go_node, cell_node, 'uberongraph.get_process_or_activity_by_cell', curie, predicate)
                    done.add(key)
                    returnresults.append((edge,go_node))
        return returnresults

    def get_cell_by_process_or_activity(self, go_node):
        returnresults = []
        for curie in go_node.get_synonyms_by_prefix('GO'):
            results = self.go_to_cell(curie)
            for direction in ['subject','object']:
                done = set()
                for r in results[direction]:
                    key = (r['p'],r['cellID'])
                    if key in done:
                        continue
                    predicate = LabeledID(Text.obo_to_curie(r['p']),r['pLabel'])
                    cell_node = KNode(r['cellID'],type=node_types.CELL,name=r['cellLabel'])
                    if direction == 'subject':
                        edge = self.create_edge(go_node, cell_node, 'uberongraph.get_cell_by_process_or_activity', curie, predicate)
                    else:
                        edge = self.create_edge(cell_node, go_node, 'uberongraph.get_cell_by_process_or_activity', curie, predicate)
                    done.add(key)
                    returnresults.append((edge,cell_node))
        return returnresults

    def get_process_or_activity_by_disease(self, disease_node):
        returnresults = []
        for curie in disease_node.get_synonyms_by_prefix('MONDO'):
            results = self.pheno_or_disease_to_go(curie)
            done = set()
            for r in results:
                key = (r['p'],r['goID'])
                if key in done:
                    continue
                predicate = LabeledID(Text.obo_to_curie(r['p']),r['pLabel'])
                go_node = KNode(r['goID'],type=node_types.BIOLOGICAL_PROCESS_OR_ACTIVITY,name=r['goLabel'])
                edge = self.create_edge(disease_node, go_node, 'uberongraph.get_process_or_activity_by_disease', curie, predicate)
                done.add(key)
                returnresults.append((edge,go_node))
        return returnresults

    def get_phenotype_by_anatomy_graph (self, anatomy_node):
        results = []
        for curie in anatomy_node.get_synonyms_by_prefix('UBERON'):
            logger.info(f"Looking up by {curie}")
            phenotypes = self.anatomy_to_phenotype (curie)
            for r in phenotypes:
                edge, node = self.create_anatomy_phenotype_edge(r['pheno_id'],r['pheno_label'],curie,anatomy_node)
                logger.info(f" got {node.id}")
                if anatomy_node.name is None:
                    anatomy_node.name = r['anatomy_label']
                results.append ( (edge, node) )
        return results

    def get_chemical_entity_by_molecular_function(self, go_node):
        results =  self.molecular_function_to_chemical(go_node.id)
        response = []
        for r in results:
            new_node = KNode(Text.obo_to_curie(r['chemical_entity']), type= node_types.CHEMICAL_SUBSTANCE)
            predicate = LabeledID(Text.obo_to_curie(r['predicate']),r['label_predicate'])
            edge = self.create_edge(go_node, new_node, 'uberongraph.get_chemical_entity_by_molecular_function', go_node.id, predicate)
            response += [(new_node, edge)]
        return response

    def get_molecular_function_by_chemical_entity(self, chebi_node):
        results = self.chemical_to_molecular_function(chebi_node.id)
        response = []
        for r in results :
            new_node = KNode(Text.obo_to_curie(r['go_id']),type= node_types.MOLECULAR_ENTITY)
            predicate = LabeledID(Text.obo_to_curie(r['predicate']), r['label_predicate'])
            edge = self.create_edge(chebi_node, new_node, 'uberongraph.get_molecular_function_by_chemical_entity', chebi_node.id, predicate)
            response += [(new_node, edge)]
        return response