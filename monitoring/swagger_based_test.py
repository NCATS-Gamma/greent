import requests
import json




def fill_path(path, parameters, robokop_host):
    """
    Generates a new string with the path variables filled in
    :param path: URL template from swagger.
    :param parameters: Default valued templates on the swagger.
    """

    parameter_formatted = {p['name']: p.get('default', p.get('example', '')) for p in parameters}
    p = ''
    try :
        p = f"{robokop_host}{path.format(**parameter_formatted)}"
    except:
        print(f'unable to resolve path parameters. skipping {path}')
    return p

def resolve_example_schema(spec, path):
    if len(path) > 1:
        return resolve_example_schema(spec[path[0]], path[1:])
    else:
        return spec.get(path[0], {}).get('example', {})

def format_requests(spec, robokop_host):
    to_send = []
    for path, meta in spec['paths'].items():
        for request_method in meta:
            if request_method == 'post':
                continue
            params = meta[request_method].get('parameters', [])
            proper_path = fill_path(path, parameters=params, robokop_host=robokop_host)
            # skip api definations that don't have values to punch into paths
            if proper_path:
                to_send.append({
                    'method': request_method,
                    'path': proper_path
                })
    return to_send


def make_requests(spec, exclude_path, robokop_host):
    to_send = format_requests(spec, robokop_host= robokop_host)
    errors = []
    for r in to_send:
        skip = False
        for p in exclude_path:
            if r['path'].startswith(p):
                skip = True
        if skip:
            continue
        response = requests.get(r['path'])
        if response.status_code >= 300:
            errors.append(
                (
                    r['path'],
                    response.status_code,
                    response.content.decode('utf-8')
                )
            )
    return errors


def test_endpoints(get_swagger_docs, excluded_path, robokop_host = 'https://robokop.renci.org'):
    errors = make_requests(get_swagger_docs, excluded_path, robokop_host)
    # reporting errors
    print(json.dumps(errors, indent=2))
    assert len(errors) == 0
