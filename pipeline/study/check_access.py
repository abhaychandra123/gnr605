"""Read-only access check. Never prints credentials or requests interactive login."""
import argparse
import importlib.util
import json
import urllib.request


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project', help='Earth Engine enabled Google Cloud project ID')
    args = parser.parse_args()
    result = {'earthengine_package': importlib.util.find_spec('ee') is not None}
    for name, url in [('public_data_network', 'https://data.chc.ucsb.edu/'),
                      ('google_api_network', 'https://earthengine.googleapis.com/')]:
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                result[name] = {'reachable': True, 'http_status': response.status}
        except urllib.error.HTTPError as error:
            result[name] = {'reachable': True, 'http_status': error.code}
        except Exception as error:
            result[name] = {'reachable': False, 'error': str(error)}
    if args.project and result['earthengine_package']:
        import ee
        try:
            ee.Initialize(project=args.project)
            result['earthengine_authenticated_request'] = ee.Number(1).getInfo() == 1
        except Exception as error:
            # Error class only: OAuth responses can contain sensitive details.
            result['earthengine_authenticated_request'] = False
            result['earthengine_error_type'] = type(error).__name__
    else:
        result['earthengine_authenticated_request'] = 'not_attempted_missing_project_or_package'
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
