# from crawler.program_runner import get_identifiers
from greent.graph import GraphDB
import crawler.program_runner
#method that gets the concepts that a service supports



def run_per_service(service_name, rosetta):
    triplets = get_supported_types(service_name, rosetta)
    for triplet in triplets:
        bake_programs(triplet, rosetta)




def get_supported_types(service_name, rosetta):
    ####
    # Grab the operations that we use along with the types it supports
    # Basic sting match is too dangerous going to make sure we have the service name
    # that is registered  in rosetta.core.
    #
    ####
    with rosetta.type_graph.driver.session() as session:
        graph_db = GraphDB(session)
        result = list(filter(lambda y: y[1],
                map(lambda x: (x['source'], x['predicate'],x['target']) , 
                    graph_db.query( """
                    MATCH (c1:Concept)-[e]->(c2:Concept) 
                        return c1.name as source, e.op as predicate, c2.name as target
                    """)
                    )))
    filtered_by_service = []
    for source, predicate, target in result:
        predicate_service = convert_predicate_to_service(predicate, rosetta.core.caster)
        if predicate_service == service_name:
            filtered_by_service.append((source, predicate, target))
    ### let's collect the predicates that have the same source and target type, but
    bucket = {}
    for source, predicate, target in filtered_by_service:
        if source not in bucket:
            bucket[source] = {}
        if target not in bucket[source]:
            bucket[source][target] = []
        if predicate not in bucket[source][target]:
            bucket[source][target].append(predicate)
    # flatten the bucket
    flat = []
    for source in bucket:
        for target in bucket[source]:
            flat.append((source, bucket[source][target], target))
    return flat



def bake_programs(triplet, rosetta):
    """
    So here we have (source, predicate op , target)
    if we filter ops with our collection we should be fine
    """
    source, operations, target = triplet
    crawler.program_runner.load_all(source,target, rosetta, 1, op_list = operations)






def convert_predicate_to_service(predicate, caster):
    """ Given a predicate like
        upcast(uberongraph~get_process_by_anatomy,biological_process_or_activity)
        input_filter(uberongraph~get_process_or_activity_by_disease,disease,typecheck~is_disease)
        panther.get_biological_process_or_activity_by_gene_family
        this function  will grab the service from it and return that/
     """
    fname = predicate
    if predicate.startswith('caster.'):
        predicate = predicate.strip('caster.')
        fname = get_function_original_function(predicate, caster).replace('~','.')
    service_name_from_graph = fname.split('.')[0]
    return service_name_from_graph



def get_function_original_function(function_text, caster):
    #recurse till we can't no more, find the inner most function,
    # caster is using the following pattern for all its functions,
    # (original_function, type, type_checker, node) so we look for
    # the original function that is not in caster object
    try:
        fname, args = caster.unwrap(function_text)
        result = args[0]
        if hasattr(caster, fname):
            result = get_function_original_function(args[0], caster)
        return result
    except:
        return function_text
