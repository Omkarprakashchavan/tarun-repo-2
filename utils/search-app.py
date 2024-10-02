import yaml
import argparse

parser = argparse.ArgumentParser('python search-app.py')
parser.add_argument('-a', '--app', required=True, help='app name')
parser.add_argument('-f', '--config', required=True, help='vtn config file')
parser.add_argument('-fs', '--fs', action='store_true', help='Check for fs Product')
args = vars(parser.parse_args())
app_name = args['app']
config_file = args['config']
fs = args['fs']

foundproject = "false"
foundfs = "false"

with open(config_file, 'r') as file:
   yaml_contents = yaml.safe_load(file)


sbom_common = yaml_contents['Generic']
for prop in sbom_common:
 if prop['name'] == 'properties':
    org_name =  prop['org-name']
    api_url =  prop['api-url']



sbom_projects = yaml_contents['Projects']
for project in sbom_projects:
 if project['name'] == app_name:
    foundproject = "true"
    if project['product-name'] == "fs":
       foundfs = "true"


if fs: 
    print(foundproject, foundfs)
else: 
    print(foundproject)
