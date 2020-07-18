import hvac
from cloudfoundry_client.client import CloudFoundryClient
import os
import json
# import environ
import subprocess
import requests
import time
# from dotenv import load_dotenv
# load_dotenv()

VAULT_URL = os.getenv("VAULT_URL")
VAULT_TOKEN = os.getenv("VAULT_TOKEN")
PAAS_ENV = os.getenv("PAAS_ENV")
PAAS_NAMESPACE = os.getenv("PAAS_NAMESPACE")
PAAS_APP_NAME = os.getenv("PAAS_APP_NAME")
CF_USERNAME = os.getenv("CF_USERNAME")
CF_PASSWORD = os.getenv("CF_PASSWORD")
CF_DOMAIN = os.getenv("CF_DOMAIN")
CF_ORG = os.getenv("CF_ORG")


def cf_get_client(username, password, endpoint, http_proxy='', https_proxy=''):
    target_endpoint = endpoint
    proxy = dict(http=http_proxy, https=https_proxy)
    client = CloudFoundryClient(target_endpoint, proxy=proxy)
    client.init_with_user_credentials(username, password)
    return client


def cf_login():
    print(f"login to cf space: {PAAS_NAMESPACE}-{PAAS_ENV}...")
    cf_client = cf_get_client(
        CF_USERNAME,
        CF_PASSWORD,
        CF_DOMAIN)
    return cf_client


def vault_get_vars():

    #breakpoint()
    client = hvac.Client(url=f'https://{VAULT_URL}', token=VAULT_TOKEN)
    print(f"Authenticated = {client.is_authenticated()}")
    print("Getting VARS from vault...")

    ## Need to check if empty it will break
    response = client.read(path=f'dit/{PAAS_NAMESPACE}/data/{PAAS_APP_NAME}/{PAAS_ENV}')
    vault_vars = f"{{'var': {(response['data']['data'])}}}"
    vault_vars = vault_vars.replace("\'", "\"")
    return vault_vars


def get_space_guid():
    #check for multiple pages returned
    #print("Get App GUID")
    response = requests.get(
                CF_DOMAIN + '/v3/spaces',
                headers={'Authorization': f'Bearer {cf_token}'})
    #print(response)
    space_response = response.json()

    #Will be better off doint this from reading in pipeline-conf not all spaces match envs
    for item in space_response['resources']:
        if item['name'] == PAAS_NAMESPACE + '-' + PAAS_ENV:
            space_guid = item['guid']
    #print(space_guid)
    return(space_guid)


def get_app_guid(cf_token):
    #breakpoint()

    space_guid = get_space_guid()

    response = requests.get(
                CF_DOMAIN + '/v3/apps',
                params={'space_guids': [space_guid, ]},
                headers={'Authorization': f'Bearer {cf_token}'})
    app_response = response.json()
    #breakpoint()
    for app_item in app_response['resources']:
        if app_item['name'] == PAAS_APP_NAME + '-' + PAAS_ENV:
            app_guid = app_item['guid']
    #print(app_guid)
    return app_guid


def clear_vars(cf_token, app_guid):
    print("Clearing old VARS...")

    response = requests.get(
                    CF_DOMAIN + '/v3/apps/' + app_guid + '/environment_variables',
                    headers={'Authorization': f'Bearer {cf_token}'})

    vars_to_clear = json.loads(response.content)['var']
    #breakpoint()
    #This is not good need to find a better way to do this.
    for item in vars_to_clear:
        vars_to_clear[item] = None
    #print(vars_to_clear)

    vars_to_clear_json = f"{{'var': {vars_to_clear}}}"
    vars_to_clear_json = vars_to_clear_json.replace("\'", "\"")
    #Python wont let you set to null directly so using None then switching out.
    vars_to_clear_json = vars_to_clear_json.replace("None", "null")
    ##########

    #breakpoint()
    response = requests.patch(
                CF_DOMAIN + '/v3/apps/' + app_guid + '/environment_variables',
                data=vars_to_clear_json,
                headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {cf_token}'})
    app_response = response.json()
    #print(app_response)


def set_vars(cf_token, app_guid, vault_vars):
    print(f"Setting VARS retrieved from vault on app: {PAAS_APP_NAME}-{PAAS_ENV}")
    #breakpoint()
    for var_item, secret in json.loads(vault_vars)['var'].items():
        print(f"{var_item}: ********** ")

    response = requests.patch(
                CF_DOMAIN + '/v3/apps/' + app_guid + '/environment_variables',
                data=vault_vars,
                headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {cf_token}'})

    app_response = response.json()


def create_app(cf_token):
    print(f"Creating app: {PAAS_APP_NAME}-{PAAS_ENV}")
    #breakpoint()
    space_guid = get_space_guid()

    json_data = {'name': f'{PAAS_APP_NAME}-{PAAS_ENV}', 'relationships': {'space': {'data': {'guid': f'{space_guid}'}}}}

    response = requests.post(
                CF_DOMAIN + '/v3/apps',
                data=json.dumps(json_data),
                headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {cf_token}'})

    app_response = response.json()
    print(app_response)


def deploy_app():
    #This should be done with the CF API (ZDT), but as this is a PoC will use the simple cf comand line

    time.sleep( 15 )

    #login
    login = subprocess.run(['cf', 'login', '-a', f'{CF_DOMAIN}', '-u', f'{CF_USERNAME}', '-p', f'{CF_PASSWORD}', '-o', f'{CF_ORG}', '-s', f'{PAAS_NAMESPACE}-{PAAS_ENV}'], stdout=subprocess.PIPE).stdout.decode('utf-8')
    print(login)
    #Create app
    create_app = subprocess.run(['cf', 'v3-create-app', f'{PAAS_APP_NAME}-{PAAS_ENV}'], stdout=subprocess.PIPE).stdout.decode('utf-8')
    print(create_app)
    #Push apps
    push_app = subprocess.run(['cf', 'push', f'{PAAS_APP_NAME}-{PAAS_ENV}', '-b', 'python_buildpack'], stdout=subprocess.PIPE).stdout.decode('utf-8')
    print(push_app)

vault_vars = vault_get_vars()

cf_client = cf_login()
cf_token = cf_client._access_token

app_guid = get_app_guid(cf_token)
clear_vars(cf_token, app_guid)
set_vars(cf_token, app_guid, vault_vars)

#This can be used when code is updated to use the CF API fpr ZDT
#create_app(cf_token)

deploy_app()
