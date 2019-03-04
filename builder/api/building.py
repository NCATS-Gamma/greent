#!/usr/bin/env python

"""Flask REST API server for builder"""

import sys
import os
import json
import requests
import logging
import yaml
from typing import NamedTuple

import redis
from flask import request
from flask_restful import Resource, reqparse
from greent.annotators import annotator_factory
from builder.api.setup import app, api
from builder.api.tasks import update_kg
import builder.api.logging_config
import greent.node_types as node_types
from greent.synonymization import Synonymizer
import builder.api.definitions
from builder.buildmain import setup
from greent.graph_components import KNode
from greent.util import LoggingUtil

rosetta_config_file = os.path.join(os.path.dirname(__file__), "..", "..", "greent", "rosetta.yml")
properties_file = os.path.join(os.path.dirname(__file__), "..", "..", "greent", "conf", "annotation_map.yaml")

logger = LoggingUtil.init_logging(__name__, level=logging.DEBUG)

class UpdateKG(Resource):
    def post(self):
        """
        Update the cached knowledge graph 
        ---
        tags: [build]
        requestBody:
            name: question
            description: The machine-readable question graph.
            content:
                application/json:
                    schema:
                        $ref: '#/definitions/Question'
            required: true
        responses:
            202:
                description: Update started...
                content:
                    application/json:
                        schema:
                            type: object
                            required:
                            - task id
                            properties:
                                task id:
                                    type: string
                                    description: task ID to poll for KG update status
        """
        task = update_kg.apply_async(args=[request.json])
        logger.info(f"KG update task start with id {task.id}")
        return {'task_id': task.id}, 202

api.add_resource(UpdateKG, '/')

class Synonymize(Resource):
    def post(self, node_id, node_type):
        """
        Return the best identifier for a concept, and its known synonyms
        ---
        tags: [util]
        parameters:
          - in: path
            name: node_id
            description: curie of the node
            schema:
                type: string
            required: true
            default: MONDO:0005737
          - in: path
            name: node_type
            description: type of the node
            schema:
                type: string
            required: true
            default: disease
        responses:
            200:
                description: Synonymized node
                content:
                    application/json:
                        schema:
                            type: object
                            properties:
                                id:
                                    type: string
                                name:
                                    type: string
                                type:
                                    type: string
                                synonyms:
                                    type: array
                                    items:
                                        type: string
        """
        greent_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..')
        sys.path.insert(0, greent_path)
        rosetta = setup(os.path.join(greent_path, 'greent', 'greent.conf'))

        node = KNode(id=node_id, type=node_type, name='')

        try:
            #synonymizer = Synonymizer(rosetta.type_graph.concept_model, rosetta)
            rosetta.synonymizer.synonymize(node)
        except Exception as e:
            logger.error(e)
            return e.message, 500

        result = {
            'id': node.id,
            'name': node.name,
            'type': node.type,
            'synonyms': list(node.synonyms)
        }
        return result, 200

api.add_resource(Synonymize, '/synonymize/<node_id>/<node_type>/')

class SynonimizeAnswerSet(Resource):
    def post(self):
        # some sanity checks
        json_blob = request.json    
        if 'knowledge_graph' in json_blob and 'nodes' in json_blob['knowledge_graph']:
            results = json_blob['knowledge_graph']['nodes']
            # make our synonymizer
            greent_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..')
            sys.path.insert(0, greent_path)
            rosetta = setup(os.path.join(greent_path, 'greent', 'greent.conf'))
            for result in results:
                if 'equivalent_identifiers' in result :
                    continue
                node = KNode(id = result['id'], type = result['type']) 
                # call synonimzer on temp node, this node will have a normalized id based on our conf.
                rosetta.synonymizer.synonymize(node)
                # set the normalized id
                result['id'] = node.id
                # result['name'] = node.name
                result['equivalent_identifiers']= [x[0] for x in list(node.synonyms)]
            return json_blob, 200
        return [], 400
api.add_resource(SynonimizeAnswerSet, '/synonymize_answer_set/')


class TaskStatus(Resource):
    def get(self, task_id):
        """
        Get the status of a task
        ---
        tags: [tasks]
        parameters:
          - in: path
            name: task_id
            description: "ID of the task"
            schema:
                type: string
            required: true
        responses:
            200:
                description: Task status
                content:
                    application/json:
                        schema:
                            type: object
                            required:
                            - task-id
                            - state
                            - result
                            properties:
                                task_id:
                                    type: string
                                status:
                                    type: string
                                    description: Short task status
                                result:
                                    type: ???
                                    description: Result of completed task OR intermediate status message
                                traceback:
                                    type: string
                                    description: Traceback, in case of task failure
        """

        r = redis.Redis(
            host=os.environ['RESULTS_HOST'],
            port=os.environ['RESULTS_PORT'],
            db=os.environ['BUILDER_RESULTS_DB'],
            password=os.environ['RESULTS_PASSWORD']
        )
        value = r.get(f'celery-task-meta-{task_id}')
        if value is None:
            return 'Task not found', 404
        result = json.loads(value)
        return result, 200

api.add_resource(TaskStatus, '/task/<task_id>')

class TaskLog(Resource):
    def get(self, task_id):
        """
        Get activity log for a task
        ---
        tags: [util]
        parameters:
          - in: path
            name: task_id
            description: ID of task
            schema:
                type: string
            required: true
        responses:
            200:
                description: text
        """

        task_log_file = os.path.join(os.environ['ROBOKOP_HOME'], 'logs','builder_task_logs', f'{task_id}.log')
        if os.path.isfile(task_log_file):
            with open(task_log_file, 'r') as log_file:
                log_contents = log_file.read()
            return log_contents, 200
        else:
            return 'Task ID not found', 404

api.add_resource(TaskLog, '/task/<task_id>/log')

class Operations(Resource):
    def get(self):
        """
        Get a JSON list of all edges in the type graph
        ---
        tags: [util]
        responses:
            200:
                description: Operations
                content:
                    application/json:
                        schema:
                            type: array
                            items:
                                type: string
        """
        with open(rosetta_config_file, 'r') as stream:
            config = yaml.load(stream)
        
        operators = config["@operators"]

        return operators

api.add_resource(Operations, '/operations')

class Connections(Resource):
    def get(self):
        """
        Get a simplified list of all edges in the type graph
        ---
        tags: [util]
        responses:
            200:
                description: Operations
                content:
                    application/json:
                        schema:
                            type: array
                            items:
                                type: string
        """
        with open(rosetta_config_file, 'r') as stream:
            config = yaml.load(stream)
        
        operations = config["@operators"]

        s = []
        for start in operations:
            for stop in operations[start]:
                s.append(f"{start} -> {stop}")

        return s

api.add_resource(Connections, '/connections')

class Properties(Resource):
    def get(self):
        """
        Get a list of all node properties that may be in the graph
        ---
        tags: [util]
        responses:
            200:
                description: Properties
                content:
                    application/json:
        """
        with open(properties_file, 'r') as stream:
            properties = yaml.load(stream)

        return properties

api.add_resource(Properties, '/properties')


class Concepts(Resource):
    def get(self):
        """
        Get known biomedical concepts
        ---
        tags: [util]
        responses:
            200:
                description: Concepts
                content:
                    application/json:
                        schema:
                            type: array
                            items:
                                type: string
        """
        concepts = list(node_types.node_types - {'unspecified'})
        return concepts

api.add_resource(Concepts, '/concepts')

if __name__ == '__main__':

    # Get host and port from environmental variables
    server_host = '0.0.0.0'
    server_port = int(os.environ['BUILDER_PORT'])

    app.run(host=server_host,\
        port=server_port,\
        debug=True,\
        use_reloader=True)
