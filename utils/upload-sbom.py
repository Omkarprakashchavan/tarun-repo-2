import copy
import requests
import os
import sys
import datetime
import json
import yaml
from json import JSONEncoder
from typing import Dict, List, Tuple
import argparse

parser = argparse.ArgumentParser('python upload-sbom.py')
parser.add_argument('-u', '--vtnuser', required=True, help='vtn user')
parser.add_argument('-p', '--vtnpswd', required=True, help='vtn api password')
parser.add_argument('-a', '--app', required=True, help='app name')
parser.add_argument('-f', '--config', required=True, help='vtn config file')
parser.add_argument('-n', '--product', required=True, help='product name')
parser.add_argument('-j', '--json', required=False, help='sbom json file',default="spdx-json_sbom_image.json")
args = vars(parser.parse_args())
vtnuser = args['vtnuser']
vtnpassword = args['vtnpswd']
app_name = args['app']
config_file = args['config']
product_name_given = args['product']
sbom_file = args['json']


### default release date assigning one year from now
date_now = datetime.date.today()
years_to_add = date_now.year + 1
date_1 = date_now.strftime('%Y-%m-%d')
month_day = date_now.strftime('%m-%d')
if month_day == '02-29':
    release_date = date_now.replace(year=years_to_add, month=3).strftime('%Y-%m-%d')
else:
    release_date = date_now.replace(year=years_to_add).strftime('%Y-%m-%d')

### default product_master_name and product_oid
product_master_name = 'NA'
product_oid = 'NA'
product_type = 'internal'
product_found = False

with open(config_file, 'r') as file:
   yaml_contents = yaml.safe_load(file)

sbom_common = yaml_contents['Generic']
for prop in sbom_common:
 if prop['name'] == 'properties':
    org_name =  prop['org-name']
    api_url =  prop['api-url']
    devops_users =  prop['devops-users']
    devops_bot =  prop['devops-bot']

class Dictdata1:
    def __init__(self, vtnuser, vtnpassword):
        self.email = vtnuser
        self.password = vtnpassword
class EmployeeEncoder(JSONEncoder):
        def default(self, o):
            return o.__dict__
deploy_data = Dictdata1( vtnuser, vtnpassword )

#####################Session token##################

def http_request(url: str, method: str = 'GET',
                 headers=None, data=None, suppress_stack_trace=False,
                 ) -> requests.models.Response:
    if not headers:
        headers = {
                  'accept': 'accept: application/json',
                  'Content-Type' : 'application/json'
                  }
    try:
        resp : requests.models.Response = \
                  requests.request(method, url, headers=headers, data=data, verify = False, timeout=120
                             )
        resp.raise_for_status()
        return resp
    except Exception as e:
        if not suppress_stack_trace:
           data = resp.json()
           print  (data)
           print(f"something went wrong with creating session token \nurl={url}\ndata={data}\n")
        else:
           return None
        sys.exit(9)

def create_session(vtn_user: str, vtn_password: str):
        url : str = f'{api_url}/login/app_login'
        resp = http_request(url, method='POST', data=json.dumps(deploy_data, indent=4, cls=EmployeeEncoder))
        json_data : Dict[str,any] = json.loads(resp.text)
        return json_data['data']['token']['token']

token = create_session( vtnuser, vtnpassword )
#### default header
headers = {
    'accept': 'application/json',
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {token}',
}

def upload_request(url: str, token: str,method: str = 'POST',
                 headers=None, files=None, suppress_stack_trace=False,
                 ) -> requests.models.Response:
    headers = {
    "accept": "multipart/form-data",
    "Authorization": f'Bearer {token}',
    }
    files = {
    'product_version': (None, product_version),
    'distribution_list_name': (None, dl_name),
    'complete_override': (None, 'true'),
    'organization_name': (None, org_name),
    'product_name': (None, full_product_name),
    'file': ((f'{sbom_file}'), open(f'{sbom_file}', 'rb'),'application/json'),
    'signed': (None, 'true'),
    }

    try:
        resp : requests.models.Response = \
                  requests.request(method, url, headers=headers, files=files, verify=False, timeout=120
                             )
        resp.raise_for_status()
        data = resp.json()
        print  (data)
        return resp
    except Exception as e:
        if not suppress_stack_trace:
           data = resp.json()
           print  (data)
           print(f"something went wrong with uploading sbom\nurl={url}\nheaders={headers}\nfiles={files}\n")
        else:
           print(f"Successfully uploaded sbom to VTN")
           return None
        sys.exit(9)

def upload_sbom(token: str):
        url : str = f'{api_url}/inventory/import'
        upload_request(url, token, method='POST')

def create_dl(url: str, token: str,method: str = 'POST',
                 headers=headers, json=None, suppress_stack_trace=False,
                 ) -> requests.models.Response:
    json_data = {
    'Distribution_List': dl_name,
    'Non_Manager_Contacts': nonmgr_mail,
    'Manager_Contacts': mgr_mail,
    'Reminder': 3,
    'Interval': 7,
    }

    try:
        resp : requests.models.Response = \
                  requests.request(method, url, headers=headers, json=json_data, verify=False, timeout=120
                             )
        resp.raise_for_status()
        data = resp.json()
        print  (data)
        return resp
    except Exception as e:
        if not suppress_stack_trace:
           data = resp.json()
           print  (data)
           print(f"something went wrong with creating dl \nurl={url}\nheaders={headers}\njson_data={json_data}\n")
           return resp
        else:
           return None
        sys.exit(9)

def delete_dl(did: str, url: str, token: str,method: str = 'POST',
                 headers=headers, json=None, suppress_stack_trace=False,
                 ) -> requests.models.Response:

    json_data = {
    'ID_Distribution_List': [
        did,
    ],
    }

    try:
        resp : requests.models.Response = \
                  requests.request(method, url, headers=headers, json=json_data, verify=False, timeout=120
                             )
        resp.raise_for_status()
        data = resp.json()
        print  (data)
        return resp
    except Exception as e:
        if not suppress_stack_trace:
           data = resp.json()
           print  (data)
           print(f"something went wrong with updating dl\nurl={url}\nheaders={headers}\njson_data={json_data}\n")
        else:
           return None

def modify_dl(url: str, token: str,method: str = 'PUT',
                 headers=headers, json=None, suppress_stack_trace=False,
                 ) -> requests.models.Response:

    json_data = {
    'Distribution_List': dl_name,
    'Non_Manager_Contacts': nonmgr_mail,
    'Manager_Contacts': mgr_mail,
    'Reminder': 3,
    'Interval': 7,
    }

    try:
        resp : requests.models.Response = \
                  requests.request(method, url, headers=headers, json=json_data, verify=False, timeout=120
                             )
        resp.raise_for_status()
        data = resp.json()
        print  (data)
        return resp
    except Exception as e:
        if not suppress_stack_trace:
           data = resp.json()
           print  (data)
           print(f"something went wrong with updating dl \nurl={url}\nheaders={headers}\njson_data={json_data}\n")
           return resp
        else:
           return None
        sys.exit(9)

def update_product(url: str, token: str,method: str = 'PUT',
                 headers=headers, json=None, suppress_stack_trace=False,
                 ) -> requests.models.Response:

    json_data = {
    'HPE_Product_Name': full_product_name,
    'HPE_Product_Version': product_version,
    'HPE_Product_Type': product_type,
    'Organization_Name': org_name,
    'Product_Master_Name': product_master_name,
    'Phase': 'In Development',
    'Product_OID': product_oid,
    'Release_Date': release_date,
    'Product_Owners': mgr_mail,
    'Read_Write_Users': devops_users,
    'Read_Only_Users': nonmgr_mail,
    }

    try:
        resp : requests.models.Response = \
                  requests.request(method, url, headers=headers, json=json_data, verify=False, timeout=120
                             )
        resp.raise_for_status()
        data = resp.json()
        print  (data)
        return resp
    except Exception as e:
        if not suppress_stack_trace:
           data = resp.json()
           print  (data)
           print(f"something went wrong with updating product \nurl={url}\nheaders={headers}\njson_data={json_data}\n")
           return resp
        else:
           return None




def get_dl(url: str, token: str,method: str = 'GET',
                 headers=headers, params=None, suppress_stack_trace=False,
                 ) -> requests.models.Response:


    params = {
    'name': dl_name,
    }

    try:
        resp : requests.models.Response = \
                  requests.request(method, url, headers=headers, params=params, verify=False, timeout=120
                             )
        resp.raise_for_status()
        json_data : Dict[str,any] = json.loads(resp.text)
        data = resp.json()
        print  (data)
        return json_data['data']['ID_Distribution_List']
    except Exception as e:
        if not suppress_stack_trace:
           data = resp.json()
           print  (data)
           print(f"something went wrong with retrieving dl\nurl={url}\nheaders={headers}\nparams={params}\n")
        else:
           return None




def update_dl(token: str):
        dist_id = get_dl(api_url+'/distribution_list', token, method='GET')
        if not dist_id:
             create_dl(api_url+'/distribution_list', token, method='POST')
        else:
             #delete_dl(dist_id, api_url+'/distribution_list/deletelist', token, method='POST')
             modify_dl(api_url+'/distribution_list/'+dist_id, token, method='PUT')

def get_product(url: str, token: str,method: str = 'GET',
                 headers=headers, params=None, suppress_stack_trace=False,
                 ) -> requests.models.Response:

    params = {
    'name': full_product_name,
    'version': product_version,
    }

    try:
        resp : requests.models.Response = \
                  requests.request(method, url, headers=headers, params=params, verify=False, timeout=120
                             )
        resp.raise_for_status()
        json_data : Dict[str,any] = json.loads(resp.text)
        data = resp.json()
        print  (data)
        return json_data['data']['ID_HPE_Product_Name']
    except Exception as e:
        if not suppress_stack_trace:
           data = resp.json()
           print  (data)
           print(f"Product Not found. Hence trying to create")
        else:
           return None


def create_product(url: str, token: str,method: str = 'POST',
                 headers=headers, json=None, suppress_stack_trace=False,
                 ) -> requests.models.Response:

    json_data = {
    'HPE_Product_Name': full_product_name,
    'HPE_Product_Version': product_version,
    'HPE_Product_Type': product_type,
    'Organization_Name': org_name,
    'Product_Master_Name': product_master_name,
    'Phase': 'In Development',
    'Product_OID': product_oid,
    'Release_Date': release_date,
    'Product_Owners': mgr_mail,
    'Read_Write_Users': devops_users,
    'Read_Only_Users': nonmgr_mail,
    }

    try:
        resp : requests.models.Response = \
                  requests.request(method, url, headers=headers, json=json_data, verify=False, timeout=120
                             )
        resp.raise_for_status()
        return resp
    except Exception as e:
        if not suppress_stack_trace:
           data = resp.json()
           print  (data)
           print(f"something went wrong with create Product")
#           print(f"something went wrong with create Product\nurl={url}\nheaders={headers}\njson_data={json_data}")
        else:
           return None
        sys.exit(9)

def get_mails(url: str, token: str,method: str = 'GET',
                 headers=headers, params=None, suppress_stack_trace=False,
                 ) -> requests.models.Response:

    params = {
    'name': dl_name,
    }

    try:
        resp : requests.models.Response = \
                  requests.request(method, url, headers=headers, params=params, verify=False, timeout=120
                             )
        resp.raise_for_status()
        json_data : Dict[str,any] = json.loads(resp.text)
        return json_data['data']['Manager_Contacts'], json_data['data']['Non_Manager_Contacts']
    except Exception as e:
        if not suppress_stack_trace:
           data = resp.json()
           print  (data)
           print(f"something went wrong with retrieving mail ids\nurl={url}\nheaders={headers}\nparams={params}\n")
        else:
           data = resp.json()
           print  (data)
           return None

#################End of functions #############################


sbom_projects = yaml_contents['Projects']

for project in sbom_projects:
 if project['name'] == app_name:
   if project['product-name'] == product_name_given:
    product_found = True
    if 'dist-list' in project.keys():
        dl_name = project['dist-list']
        mgr_mail, nonmgr_mail = get_mails(api_url+'/distribution_list', token, method='GET')
    else:
        mgr_mail = project['mgr-list']
        nonmgr_mail = project['nonmgr-list']
        dl_name = "mci-"+app_name
        update_dl( token )
    for x in devops_bot:
        mgr_mail.append(x)
    if 'product-type' in project.keys():
        product_type = project['product-type']
    if 'product-master-name' in project.keys():
        product_master_name = project['product-master-name']
    if 'product-oid' in project.keys():
        product_oid = project['product-oid']
    if 'release-date' in project.keys():
        release_date = project['release-date']
    product_name =  project['product-name']
    product_version = project['product-version']
    full_product_name = app_name+"-"+product_name
    product_id = get_product(api_url+'/hpe_product', token, method='GET')
    if product_id is None:
        print(f"Creating Product {full_product_name}")
        create_product( api_url+'/hpe_product', token )
    else:
        print(f"Product is already existing {full_product_name}")
        update_product( api_url+'/hpe_product/name/'+product_id, token )
    upload_sbom( token )


if not product_found:
    print(f"appname {app_name} and/or product name {product_name_given} not found in VTN CONFIG")
    sys.exit(9)
