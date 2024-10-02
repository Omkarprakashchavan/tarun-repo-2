
# Tue Feb 01 20:34:44 2022
import errno
import logging
import requests
import os
import platform
import shlex
import subprocess
import sys
import yaml
from datetime import datetime
from logging.handlers import RotatingFileHandler

FAILED_CMD = 256
FAILURE = 1
SUCCESS = 0

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


def file_exists(fpath, check_nonzero_filesize=False):
    '''
    Check if the specified file exists and is readable.

    Args:
        fpath (string): full path to the filename
        check_nonzero_filesize (Boolean): if True, chceck if filesize is > 0

    Returns:
        True if the file exists and is readable and file size is > 0 (if check_nonzero_filesize is specified)
    '''

    val = os.path.exists(fpath) and os.path.isfile(fpath) and os.access(fpath, os.R_OK)
    if check_nonzero_filesize:
       val = val and os.path.getsize(fpath) > 0
    return val


def get_logger(log_name, logfile, level='INFO',
               format_str='[%(asctime)s] %(levelname)s [%(filename)s:%(funcName)s:%(lineno)s] %(message)s',
               date_format="%Y-%m-%d %H:%M:%S", maxBytes=0,
               backupCount=10, output_to_console=False) -> logging.Logger:
# http://stackoverflow.com/questions/16757578/what-is-the-default-python-logging-formatter
# http://stackoverflow.com/questions/13733552/logger-configuration-to-log-to-file-and-print-to-stdout

    '''
    Wrapper function to create logger object that writes to both a logfile as well as standard output

    :param log_name (string): name of the logger
    :param logfile (string): fullpath to the logfile
    :param level (string): DEBUG, INFO, WARNING, ERROR, CRITICAL
    :param format_str: the format string of the logs
    :param date_format (string): the date format
    :return:
    '''
    logger = logging.getLogger(log_name)
    logger.setLevel(level.upper())
    formatter = logging.Formatter(format_str,date_format)

    # fh = logging.FileHandler(logfile)
    # rotate when file exceeds 10 MB
    # if maxBytes is zero (default), rollover never occurs
    fh = RotatingFileHandler(filename=logfile, maxBytes=maxBytes, backupCount=backupCount)
    fh.setLevel(level.upper())
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    if output_to_console:
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    return logger


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


# http://stackoverflow.com/questions/600268/mkdir-p-functionality-in-python
def mkdir_p(path):
    try:
       os.makedirs(path)
    except OSError as exc:  # Python >2.5
       if exc.errno == errno.EEXIST and os.path.isdir(path):
          pass
       else:
          raise


def read_file(filename: str, 
              min_num_chars: int=5, 
              skip_comment_lines=True,
              logger=no_logger):

    contents : list = []
    results : List[Tuple] = []
    with open(filename) as fh:
        contents = fh.read().splitlines()

    for i in contents:

        if not i:
            logger.debug(f'Skipping because line is null')
            continue
        if i.startswith('#') and skip_comment_lines:
            logger.debug(f'Skipping because line is a comment')
            continue
        if len(i) < min_num_chars:
            logger.debug(f'Skipping because line is less than {min_num_chars} chars long')
            continue
        #results.append(os.path.basename(i.strip()))
        results.append(i.strip())

    return results


def run_cmd(the_cmd, cwd=None, flush=False, env_file=None, shell=False, use_setsid=True, logger=no_logger):
    '''
    Run the command specified in the the_cmd (can be a string or a list).
    Change to the specified dir, if specified.
    Flush the output immediately, if specified.
    If env_file is specified, then let 'bash' handle the sourcing of the env file and also run the_cmd
    if use_setsid is True, then interactive input will NOT work properly.  Set use_setsid=False if  
      the_cmd expects user input.
    Return a list: exit_code, stdout, stderr

    '''

    output = ''
    err = ''
    ec = SUCCESS # default exit code
    output_lines = ''

    shell_mapping = {'Linux' : '/bin/bash -c ',
                     'Windows' : 'cmd.exe /c ',
                     'Darwin' : '/bin/bash -c '
                    }

    if isinstance(the_cmd, list):
       cmd = the_cmd
    else:
       cmd = shlex.split(the_cmd)

    # At this point, cmd is a list.

    os_name = platform.system()

    if env_file:
       use_shell=True
       if os_name == 'Linux':
         # Must convert back to a string because we need 'bash' to source the env file
          cmd = shell_mapping[os_name] + ' ". ' + env_file + ' && ' + ' '.join(cmd) + '"'
       else:
         # Must convert back to a string because we need 'cmd.exe' to source the env (.bat) file
          cmd = shell_mapping[os_name] + ' "' + env_file + ' && ' + ' '.join(cmd) + '"'
    elif shell:
       use_shell=True
       # Must convert back to a string if shell=True is specified
       cmd = shell_mapping[os_name] + ' "' + ' '.join(cmd) + '"'
    else:
       use_shell=False
       # if shell=False, then cmd is already a list
       # This is for backward compatibility

    logger.debug('Running cmd: {}'.format(cmd))

    try:
       if os_name == 'Linux':
          if use_setsid:
             use_setsid=os.setsid
       else:  # Not supported on Windows
          use_setsid=None
       proc = subprocess.Popen(cmd, shell=use_shell, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=use_setsid, cwd=cwd)
       if flush:
           for line in iter(proc.stdout.readline,b''):
               print(line.rstrip())
               output_lines += line
               sys.stdout.flush()
       output, err = proc.communicate()
       ec = proc.returncode
       if flush: # the flush() method wipes out the stdout variable 'output'; therefore, we need to restore it.
           output = output_lines

    except CalledProcessError as e:
       ec=FAILED_CMD
       output=e.output
    except OSError as e:
       ec=FAILED_CMD
       output="Unable to run: " +" ".join(cmd)
       output += '\n' + str(e)
    except Exception as e:
       ec=FAILED_CMD
       output="Unable to run: " +" ".join(cmd)
       output += '\n' + str(e)

    if sys.version_info.major > 2:
       # Use .decode() to get back strings in Python 3.
       # Without .decode(), 'output' and 'err' are bytes in Python 3.
       # In Python 2, these assignments have no effect.
       output = output.decode()
       err = err.decode()

    return ec, output, err

def create_log_file(module_name, module_description, repo_updates, scanned_repositories):
    if not 'date_str' in os.environ:
        cur_dt = datetime.now()
        date_today = cur_dt.strftime('%Y-%m-%d-%H-%M')
    else:
        date_today=os.environ['date_str']
    counter : int = 1
    filename=f'devops-reports/workflow-reports/workflows-deployed-{date_today}.yaml'
    mkdir_p('devops-reports/workflow-reports')
    data={'name':module_name,'description':module_description,
          'scannedRepositories':scanned_repositories,
          'deployedWorkflowsByRepository':repo_updates}
    if not file_exists(filename):
        data={'startTime':date_today,'modules':[data]}
    else:
        with open(filename,'r') as yamlfile:
                  yaml_data = yaml.safe_load(yamlfile) # Note the safe_load
                  yaml_data['modules'].append(data)
                  data=yaml_data
    with open(f"devops-reports/workflow-reports/workflows-deployed-{date_today}.yaml", mode = 'w') as f:
        f.write(yaml.dump(data, default_flow_style=False, sort_keys=False))




