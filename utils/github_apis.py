import json
import requests

from typing import Dict, List, Tuple


class NoLogger:
    """
    A dummy class to provide no-op methods in case a logging object is not available/created.
    """

    def __init__(self):
        pass

    def critical(self, msg, *args, **kwargs):
        pass

    def error(self, msg, *args, **kwargs):
        pass

    def exception(self, msg, exc_info=True, *args, **kwargs):
        pass

    def warning(self, msg, *args, **kwargs):
        pass

    def info(self, msg, *args, **kwargs):
        pass

    def debug(self, msg, *args, **kwargs):
        pass

no_logger = NoLogger()

def http_request(url: str, token: str = '', method: str = 'GET',
                 headers=None, data=None, suppress_stack_trace=False,
                 logger=no_logger) -> requests.models.Response:

    if not headers:
        headers = {
                  'Accept': 'application/vnd.github.v3+json',
                  'Authorization': f'token {token}'
                  }
    try:
        resp : requests.models.Response = \
                  requests.request(method, url, headers=headers, data=data
                             )
        resp.raise_for_status()
        return resp
        # json_data : List[Dict[str,any]] = json.loads(resp.text)
        # return json_data
    except Exception:
        if not suppress_stack_trace:
           logger.exception(f'\nsomething went wrong\nurl={url}\nmethod={method}\ndata={data}\n')
           raise
        else:
           return None


class GitHubAPIs:
    def __init__(self, org_name: str, token: str, 
                 api_url: str = 'https://api.github.com',
                 logger=no_logger):
        self._org_name = org_name  # such as 'glcp'
        self._token = token        # Github token with appropriate privileges
        self._api_url = api_url    
        self._logger = logger


    def get_default_branch(self, repo_name: str) -> Dict[str,any]:
        # Get a repository
        # https://docs.github.com/en/rest/repos/repos#get-a-repository
        # GET /repos/{owner}/{repo}
        url : str = f'{self._api_url}/repos/{self._org_name}/{repo_name}'

        self._logger.debug(f'Getting default branch in repo "{repo_name}" using {url}')
        try:
            resp = http_request(url, self._token, logger=self._logger)
            json_data : Dict[str,any] = json.loads(resp.text)
            return json_data['default_branch']
        except Exception:
            self._logger.warning(f'Could not get the default branch for repo "{repo_name}" '
                                 f'at {url}'
                                )
            return None


    def check_branch_protection_enabled(self, branch_name: str,
                                        repo_name: str) -> List[Dict[str,any]]:
        # Get branch protection
        # GET /repos/{owner}/{repo}/branches/{branch}/protection

        url : str = f'{self._api_url}/repos/{self._org_name}/{repo_name}/branches/{branch_name}'
        self._logger.debug(f'Getting branch protection info status for branch "{branch_name}" at {url}')
        resp = http_request(url, self._token, method='GET', logger=self._logger)
        json_data : List[Dict[str,any]] = json.loads(resp.text)
        return json_data['protected']


    def delete_branch_protection(self, branch_name: str, repo_name: str):
        # Delete branch protection
        # DELETE /repos/{owner}/{repo}/branches/{branch}/protection
        url = f'{self._api_url}/repos/{self._org_name}/{repo_name}/branches/{branch_name}/protection'
        self._logger.debug(f'Deleting branch protection for branch "{branch_name}" '
                     f'in org/repo "{self._org_name}/{repo_name}" using {self._api_url}')
        http_request(url, self._token, method='DELETE')



    def get_branch_protection(self, branch_name: str, repo_name: str) -> List[Dict[str,any]]:
        # Get branch protection
        # GET /repos/{owner}/{repo}/branches/{branch}/protection

        url : str = f'{self._api_url}/repos/{self._org_name}/{repo_name}/branches/{branch_name}/protection'
        self._logger.debug(f'Getting branch protection info for branch "{branch_name}" at {url}')
        resp = http_request(url, self._token, method='GET', logger=self._logger)
        json_data : List[Dict[str,any]] = json.loads(resp.text)
        return json_data


    def set_branch_protection(self, protection_data: Dict[str, any], 
                              branch_name: str, repo_name: str):
        # Update branch protection
        # PUT /repos/{owner}/{repo}/branches/{branch}/protection
        url : str = f'{self._api_url}/repos/{self._org_name}/{repo_name}/branches/{branch_name}/protection'
        self._logger.debug(f'Setting branch protection info for branch "{branch_name}" at {url}')
        http_request(url, self._token, method='PUT', data=json.dumps(protection_data), logger=self._logger)
        self._logger.debug(f'Done setting branch protection info for branch "{branch_name}" at {url}')

    def get_repo_names_in_org(self, max_pages: int = 2000) -> List[str]:
        # List organization repositories
        # GET /orgs/{org}/repos
        url_fmt : str = f'{self._api_url}/orgs/{self._org_name}/repos?page={{pagenum}}'
        repo_names : List[str] = []

        for page in range(max_pages):
            url : str = url_fmt.format(pagenum=page+1)
            resp = http_request(url, self._token, method='GET', logger=self._logger)
            json_data : List[Dict[str,any]] = json.loads(resp.text)
            if not json_data:  # if empty, then exit loop
                break
            # print(f'==========={len(json_data)}')
            # print(json.dumps(json_data, indent=2))
            for adict in json_data:
                repo_names.append(adict['name'])
        return repo_names


    def check_workflow_file(self, repo_name: str, workflow_file: str) -> List[Dict[str,any]]:
        # Get pull_request_template info
        # GET /repos/{owner}/{repo}/branches/contents/PATH
        # found=False
        url : str = f'{self._api_url}/repos/{self._org_name}/{repo_name}/contents/.github/workflows/{workflow_file}'
        # self._logger.debug(f'Getting pull request template info status for repo "{repo_name}" at {url}')
        try:
            resp = http_request(url, self._token, method='GET', suppress_stack_trace=True, logger=self._logger)
            json_data : List[Dict[str,any]] = json.loads(resp.text)
            self._logger.debug(f'''Size of file {workflow_file} is {json_data['size']}''')
            if json_data['size'] > 0:
                return True
            else:
                self._logger.warning(f'File {workflow_file} in repo  "{repo_name}" is 0 bytes....Skipping')                   
        except requests.exceptions.HTTPError:
            return False
        except AttributeError:
            return False
        return False

    def check_is_repo_archived(self, repo_name: str) -> Dict[str,any]:
        # Get a repository
        # https://docs.github.com/en/rest/repos/repos#get-a-repository
        # GET /repos/{owner}/{repo}
        url : str = f'{self._api_url}/repos/{self._org_name}/{repo_name}'

        self._logger.debug(f'Getting repo archive state for "{repo_name}" using {url}')
        try:
            resp = http_request(url, self._token, logger=self._logger)
            json_data : Dict[str,any] = json.loads(resp.text)
            return json_data['archived']
        except Exception:
            self._logger.warning(f'Could not get the archive state for repo "{repo_name}" '
                                 f'at {url}'
                                )
            return None


