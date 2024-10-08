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
from pathlib import Path
import trace

# Set up the tracer
tracer = trace.Trace(count=False, trace=True)

sys.path.append(f'{os.path.dirname(__file__)}/..')
import subprocess
from os import listdir
from os.path import isfile, join

import requests
import json

print('HELLllllllllo')

def load_yaml(file_content):
    """Read workflow-deployment.yaml content into a dictionary."""
    return yaml.safe_load(file_content)

def get_file_content_from_commit(repo, commit_sha, file_path):
    """Get the content of a file from a specific commit SHA."""
    commit = repo.commit(commit_sha)
    try:
        file_blob = commit.tree[file_path]
        file_content = file_blob.data_stream.read().decode('utf-8')
        return file_content
    except KeyError:
        raise ValueError(f"File '{file_path}' does not exist in commit {commit_sha}")

def get_second_top_commit(repo_path):
    # Open the repository
    repo = git.Repo(repo_path)
    # Ensure we're working with the 'main' branch
    try:
        branch = repo.heads.main
    except AttributeError:
        raise ValueError("The repository does not have a branch named 'main'.")
    # Get the list of commits in the branch
    commits = list(repo.iter_commits(branch.name, max_count=2))
    print(commits)
    if len(commits) < 2:
        raise ValueError("There are less than two commits in the 'main' branch.")
    # The second most recent commit will be the second item in the list
    second_top_commit = commits[1]
    commit = repo.commit(commits[0])
    parent_commit = commit.parents[0] if commit.parents else None
    if parent_commit:
        diff = commit.diff(parent_commit)
        changed_files = []
        for change in diff:
            file_info = {
                'file': change.a_path,  # the file name
                'change_type': change.change_type  # 'A', 'M', or 'D'
            }
            changed_files.append(file_info)
        print(changed_files)
    return second_top_commit

def compare_repositories(repo_list1, repo_list2):
    """Compare two lists of repositories and return the differences."""
    changes = {'repositories': []}
    # Convert list of dictionaries to a list of unique identifiers (name and refspec)
    def get_repo_identifiers(repo_list):
        return {(repo.get('name'), repo.get('refspec')): repo for repo in repo_list}
    # Convert both lists to identifiers
    repo_dict1 = get_repo_identifiers(repo_list1)
    repo_dict2 = get_repo_identifiers(repo_list2)
    # Find repositories in repo_dict2 that are not in repo_dict1
    for key, repo in repo_dict2.items():
        if key not in repo_dict1:
            changes['repositories'].append(repo)
    # Find repositories that exist in both dicts but have different contents
    for key in repo_dict1.keys():
        if key in repo_dict2 and repo_dict1[key] != repo_dict2[key]:
            changes['repositories'].append(repo_dict2[key])
    # If no changes, return an empty dictionary
    if not changes['repositories']:
        return {}
    return changes

api_url = 'https://api.github.com/graphql'
# github_token = os.environ['GITHUB_APP_TOKEN']
organisation = 'Omkarprakashchavan'
repositories = []
# headers = {
#     'Authorization': f'Bearer {github_token}',
#     'Content-Type': 'application/json'
# }

logger: Union[logging.Logger, None] = None
gh_obj = None
topdir = os.path.dirname(os.path.abspath(sys.argv[0]))
logdir = f'{topdir}/logdir'
file_name_pattern='managed-ci'

versioned_ci_repo = f'{os.path.dirname(__file__)}/../tarun-repo-config'
arr = os.listdir()
print(arr)
print(f'versioned CI Repo {versioned_ci_repo}')
repo_path = versioned_ci_repo
# file_path = 'tarun-repo-config/configs/workflow-deployment.yaml'
file_path = 'workflow-deployment.yaml'
print(f' file path ------ {file_path}')
mod_path = Path(__file__).parent
relative_config_path = '../tarun-repo-config/'
src_path_1 = (mod_path / relative_config_path).resolve()
# deployment_workflow_path = str((mod_path / relative_config_path / 'configs' / 'workflow-deployment.yaml').resolve())
deployment_workflow_path = 'configs/workflow-deployment.yaml'
print(f'deployment_workflow_path ============= {deployment_workflow_path}')
print(f'{mod_path},-------------------- {src_path_1}')
repo_path = src_path_1
print(f'printing version ci repo name {versioned_ci_repo} {repo_path}')
repo = git.Repo(repo_path)
try:
  main_branch = repo.heads.main
  print(f'main branch name {main_branch}')
except AttributeError:
  raise ValueError("The repository does not have a branch named 'main'.")

latest_commit_sha = main_branch.commit.hexsha
second_top_commit = get_second_top_commit(repo_path)
print(f"Latest commit SHA of 'main': {latest_commit_sha}")
try:
  file_commit_sha = get_file_content_from_commit(repo, latest_commit_sha, deployment_workflow_path)
  # print(f"Commit SHA of '{file_path}' in the latest commit: {file_commit_sha}")
except ValueError:
  print(f"File '{file_path}' does not exist in the latest commit {latest_commit_sha}")

try:
  content_old = get_file_content_from_commit(repo, second_top_commit, deployment_workflow_path)
  content_new = get_file_content_from_commit(repo, latest_commit_sha, deployment_workflow_path)
except ValueError as e:
  print(e)

dict_old = load_yaml(content_old)
dict_new = load_yaml(content_new)
# Extract repositories data from dict1 and dict2
repositories1 = dict_old['modules'][0]['repositories']
repositories2 = dict_new['modules'][0]['repositories']

changed_repositories = compare_repositories(repositories1, repositories2)
print(f'Changed repositories: {changed_repositories}')
