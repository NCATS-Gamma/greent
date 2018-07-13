"""
API definitions
"""

from builder.api.setup import swagger
from builder.util import FromDictMixin
@swagger.definition('Node')
class Node(FromDictMixin):
    """
    Node Object
    ---
    id: Node
    required:
        - id
    properties:
        id:
            type: string
        type:
            type: string
        curie:
            type: string
    """
    def __init__(self, *args, **kwargs):
        self.id = None
        self.type = None
        self.identifiers = []

        super().__init__(*args, **kwargs)

    def dump(self):
        return {**vars(self)}

@swagger.definition('Edge')
class Edge(FromDictMixin):
    """
    Edge Object
    ---
    id: Edge
    required:
        - source_id
        - target_id
    properties:
        source_id:
            type: string
        target_id:
            type: string
        min_length:
            type: integer
            default: 1
        max_length:
            type: integer
            default: 1
    """
    def __init__(self, *args, **kwargs):
        self.source_id = None
        self.target_id = None
        self.min_length = 1
        self.max_length = 1

        super().__init__(*args, **kwargs)

    def dump(self):
        return {**vars(self)}

@swagger.definition('Question')
class Question(FromDictMixin):
    """
    Question
    ---
    id: Question
    required:
      - nodes
      - edges
    properties:
        machine_question:
            type: object
            properties:
                nodes:
                    type: array
                    items:
                        $ref: '#/definitions/Node'
                edges:
                    type: array
                    items:
                        $ref: '#/definitions/Edge'
    example:
        machine_question:
            nodes:
              - id: 0
                type: disease
                curie: "MONDO:0005737"
                name: "Ebola hemorrhagic fever"
              - id: 1
                type: gene
              - id: 2
                type: genetic_condition
            edges:
              - source_id: 0
                target_id: 1
              - source_id: 1
                target_id: 2
    """

    def __init__(self, *args, **kwargs):
        '''
        keyword arguments: id, user, notes, natural_question, nodes, edges
        q = Question(kw0=value, ...)
        q = Question(struct, ...)
        '''
        # initialize all properties
        self.nodes = [] # list of nodes
        self.edges = [] # list of edges

        super().__init__(*args, **kwargs)

    def preprocess(self, key, value):
        if key == 'nodes':
            return [Node(n) for n in value]
        elif key == 'edges':
            return [Edge(e) for e in value]

    def dump(self):
        return {**vars(self)}