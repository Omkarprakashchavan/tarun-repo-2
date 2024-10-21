# Import hashlib library (md5 method is part of it)
import hashlib
import logging
import os
import sys
from typing import Dict, List, Union
from datetime import datetime
import git
import yaml
from ruamel.yaml import YAML

sys.path.append(f'{os.path.dirname(__file__)}/..')
import subprocess
import utils.myutils as mu
from utils.myutils import file_exists, mkdir_p
from utils.github_apis import GitHubAPIs
from os import listdir
from os.path import isfile, join

import requests
import json

api_url = 'https://api.github.com/graphql'
github_token = os.environ['GITHUB_APP_TOKEN']
organisation = 'glcp'
repositories = []
headers = {
    'Authorization': f'Bearer {github_token}',
    'Content-Type': 'application/json'
}

logger: Union[logging.Logger, None] = None
gh_obj = None
topdir = os.path.dirname(os.path.abspath(sys.argv[0]))
logdir = f'{topdir}/logdir'
file_name_pattern='managed-ci'

def main(module_name='', module_description='', repositories=[], default_managed_refspec=None):
    if not 'ORG_NAME' in os.environ:
        org_name='glcp'
    else:
        org_name=os.environ['ORG_NAME']
    global managed_ci_workflow_repo
    managed_ci_workflow_repo='managed-ci-workflow'

    app_token = os.environ.get("GITHUB_APP_TOKEN", '')

    mu.mkdir_p(logdir)
    global logger
    global gh_obj
    ## Change values accordingly in get_logger()
    logger = mu.get_logger('workflow-deployer', f'{logdir}/workflow-deployer.log', level='debug', output_to_console=True)
    gh_obj = GitHubAPIs(org_name=org_name, token=app_token, logger=logger)
    org_repos : List[str] = gh_obj.get_repo_names_in_org()

    logger.debug(f'Final list of Repos in the glcp org')
    versioned_ci_repo = f'{os.path.dirname(__file__)}/../{managed_ci_workflow_repo}'
    if os.environ['RUN_EVENT'] == 'push':
        repo_path = versioned_ci_repo
        file_path = 'workflow-deployment.yaml'

        ########################################## Testing for changes in workflow-deployment.yaml #################################
        repo = git.Repo(repo_path)
        try:
            main_branch = repo.heads.main
        except AttributeError:
            raise ValueError("The repository does not have a branch named 'main'.")

        latest_commit_sha = main_branch.commit.hexsha
        second_top_commit = get_second_top_commit(repo_path)
        # print(f"Latest commit SHA of 'main': {latest_commit_sha}")
        try:
            file_commit_sha = get_file_content_from_commit(repo, latest_commit_sha, file_path)
            # print(f"Commit SHA of '{file_path}' in the latest commit: {file_commit_sha}")
        except ValueError:
            print(f"File '{file_path}' does not exist in the latest commit {latest_commit_sha}")

        try:
            content_old = get_file_content_from_commit(repo, second_top_commit, file_path)
            content_new = get_file_content_from_commit(repo, latest_commit_sha, file_path)
        except ValueError as e:
            print(e)

        dict_old = load_yaml(content_old)
        dict_new = load_yaml(content_new)
        # Extract repositories data from dict1 and dict2
        repositories1 = dict_old['modules'][0]['repositories']
        repositories2 = dict_new['modules'][0]['repositories']

        changed_repositories = compare_repositories(repositories1, repositories2)

        print(f'Changed repositories: {changed_repositories}')

        ############################################################################################################################################
    else:
        print("RUN EVENT is not a push event, hence running the script normally")
      
