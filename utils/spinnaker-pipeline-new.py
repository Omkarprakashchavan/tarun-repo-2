import json
import sys
import time

import requests
import urllib3
import argparse

class SpinnakerHelper(object):
    def __init__(self, env, key, spinnaker_url):
        if not env:
            raise RuntimeError("Environment is required.")
        self.env = env
        if spinnaker_url:
            self.url = spinnaker_url       
        else:
            if self.env == "qa":
                self.url = "https://spinnaker-qa-api.ccs.arubathena.com:8085/"
            elif self.env == "prod":
                self.url = "https://spinnaker-api.common.cloud.hpe.com:8085/"
        if not key:
            raise RuntimeError("Certificate file is required.")
        self.key = key

    def trigger_spinnaker_pipeline(self, relative_url, payload):
        try:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            url = self.url + str(relative_url)
            # print("url in python: {}".format(url))
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            # print("Payload in python: {}".format(payload))
            r = requests.post(
                url, data=payload, cert=self.key, verify=False, headers=headers
            )
            output = json.loads(r.content)
            response_dict = {"status": None, "pipeline_id": None}
            if r.status_code != 202:
                response_dict.update({"status": r.status_code})
                raise RuntimeError(r)
            response_dict.update({"status": r.status_code})
            response_dict.update({"pipeline_id": output["ref"][11:]})
            # print(output["ref"][11:])
            # print(response_dict)
            # print(response_dict["pipeline_id"])
            self.poll_spinnaker_pipeline_status(pipeline_id=response_dict["pipeline_id"])
            return
        except Exception as e:
            # print(e)
            print("ERROR")

    def poll_spinnaker_pipeline_status(self, pipeline_id):
        # print("Polling pipeline status..")
        while True:
            # print("Sleeping for 30 seconds..")
            time.sleep(30)
            url = self.url + "pipelines/" + str(pipeline_id)
            # print("URL while polling: {}".format(url))
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            poll = requests.get(url, cert=self.key, verify=False, headers=headers)
            output = json.loads(poll.content)
            if output["status"] == "SUCCEEDED":
                print("Spinnaker pipeline has completed successfully")
                break
            elif output["status"] == "CANCELED":
                # print("Spinnaker pipeline has been cancelled...")
                raise Exception("ERROR: Spinnaker pipeline has been cancelled...")
                break
            elif output["status"] == "TERMINAL":
                # print("Spinnaker pipeline task has exited due to container error.")
                raise Exception("ERROR: Spinnaker pipeline task has exited due to container error.")
                break
        return


if __name__ == "__main__":
    argParser = argparse.ArgumentParser()
    argParser.add_argument("-e", "--environment", help="The environment to be used", required=True)
    argParser.add_argument("-k", "--key", help="The pem key used to connect to the cluster",required=True)
    argParser.add_argument("-U", "--url", help="spinnaker URL for the deployment",required=False)
    argParser.add_argument("-p", "--payload", help="Payload used in the deployment",required=True)
    argParser.add_argument("-u", "--relative_url", help="Spinnaker path to the deployemnt pipeline",required=True)
    args = argParser.parse_args()
    env = args.environment
    key = args.key
    relative_url = args.relative_url
    spinnaker_url = args.url
    if spinnaker_url == 'skip':
        spinnaker_url = False
    payload = args.payload
    spin = SpinnakerHelper(env, key, spinnaker_url)
    spin.trigger_spinnaker_pipeline(relative_url, payload)