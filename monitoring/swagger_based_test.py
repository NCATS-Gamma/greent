import requests
import json

robokop_host = 'https://robokop.renci.org'


def fill_path(path, parameters):
    """
    Generates a new string with the path variables filled in
    :param path: URL template from swagger.
    :param parameters: Default valued templates on the swagger.
    """

    parameter_formatted = {p['name']: p.get('default', p.get('example', '')) for p in parameters}
    return f"{robokop_host}{path.format(**parameter_formatted)}"

def resolve_example_schema(spec, path):
    if len(path) > 1:
        return resolve_example_schema(spec[path[0]], path[1:])
    else:
        return spec.get(path[0], {}).get('example', {})

def format_requests(spec):
    to_send = []
    for path, meta in spec['paths'].items():
        for request_method in meta:
            params = meta[request_method].get('parameters', [])
            body_container = meta[request_method].get('requestBody', {}).get('content', {}).get('application/json', {})
            # if we have schema defined use it to resolve or else we will look for an example
            schema_ref = body_container.get('schema', {}).get('$ref', '')
            if schema_ref:
                body = resolve_example_schema(spec, schema_ref.strip('#/').split('/'))
            else:
                body = body_container.get('example', {})
            to_send.append({
                'method': request_method,
                'body': body,
                'path': fill_path(path, parameters=params)
            })
    return to_send


def make_requests(spec, exclude_path):
    to_send = format_requests(spec)
    errors = []
    for r in to_send:
        if r['path'] in exclude_path:
            continue
        if r['method'] == 'get':
            response = requests.get(r['path'])
            if response.status_code >= 300:
                errors.append(
                    (
                        r['path'],
                        response.status_code,
                        response.content
                    )
                )
        if r['method'] == 'post':
            response = requests.post(r['path'], json=r['body'])
            if response.status_code >= 300:
                errors.append(
                    (
                        r['path'],
                        response.status_code,
                        response.content.decode('utf-8'),
                        r['body']
                    )
                )
    return errors


def test_endpoints(get_swagger_docs, excluded_path):
    errors = make_requests(get_swagger_docs, excluded_path)
    print(json.dumps(errors))
    assert len(errors) == 0
