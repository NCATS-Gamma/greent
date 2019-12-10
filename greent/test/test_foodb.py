import pytest
from greent.services.foodb import FooDB
from greent.servicecontext import ServiceContext
from greent.graph_components import KNode
from greent import node_types
import os

@pytest.fixture()
def foodb(rosetta):
    foodb = rosetta.core.foodb
    return foodb

#The tests in this file are not good.
#If they rely on this data file, then it needs to be pulled from somewhere or be part of the repository.


def _test_load_foods(foodb: FooDB):
    # load up the foods.csv file
    home = os.environ.get('ROBOKOP_HOME')
    results = foodb.load_all_foods(f'{home}/robokop-interfaces/crawler/foods.csv')

    assert results


def _test_food_to_chemical_substance(foodb: FooDB):
    # load up the foods.csv file
    home = os.environ.get('ROBOKOP_HOME')
    food_list = foodb.load_all_foods(f'{home}/robokop-interfaces/crawler/foods.csv')

    # create a food node
    food_node = KNode(id=food_list[1], type=node_types.FOOD)

    # call to create and populate the chemical substance nodes/edges
    cs_nodes_and_edges = foodb.food_to_chemical_substance(food_node)

    # TODO: synonymize the chemical substance node

    assert cs_nodes_and_edges
