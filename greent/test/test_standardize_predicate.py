import pytest
from greent.graph_components import LabeledID
from greent import node_types
from greent.util import Text
from greent.conftest import rosetta


def test_contributes_to(rosetta):
    """Spot check that standardizing causes_or_contributes_to goes to causes"""
    concept_model = rosetta.type_graph.concept_model
    predicate_id = LabeledID(identifier='RO:0003302', label='causes_or_contributes_to')
    standard = concept_model.standardize_relationship(predicate_id)
    assert standard.identifier == 'RO:0002410'
    assert standard.label == 'causes'


