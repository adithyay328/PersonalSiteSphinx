# This script initializes the entire build process,
# and starts up the webhook handler for incremental
# rebuilds.

""" 
During initialization, we do the followng:
 1. Run the build process. This gets the current state
    of the repo up to the current state of the repo.
 2. Fire up an ngrok tunnel, and create a github webhook
    to listen for branch or commit updates. If a prior
    webhook existed, delete that first
"""

import time
import os
import random
import json
import subprocess
from string import Template

from pyngrok import ngrok
from github import Github
from github import Auth

import buildUtils

"""CONFIG CONSTANTS"""
GITHUB_WEBHOOK_ID_JSON_FNAME = "webhook_id.json"
ENV_VARIABLE_JSON_FNAME = "env.json"
ENV_OBJ = {}
BUILD_CONFIG_JSON_FNAME = "buildConfig.json"
BUILD_CONFIG_OBJ = {}
WEBHOOK_LISTENER_PY_FNAME = "webhookListener.py"

with open(ENV_VARIABLE_JSON_FNAME) as f:
  ENV_OBJ.update(json.loads(f.read()))

with open(BUILD_CONFIG_JSON_FNAME) as f:
  BUILD_CONFIG_OBJ.update(json.loads(f.read()))

GH_USERNAME = BUILD_CONFIG_OBJ["repo_owner_username"]
GH_REPO_NAME = BUILD_CONFIG_OBJ["repo_name"]

GITHUB_PERSONAL_ACCESS_TOKEN = ENV_OBJ["GITHUB_PERSONAL_ACCESS_TOKEN"]
GH_AUTH = Auth.Token(GITHUB_PERSONAL_ACCESS_TOKEN)
GH = Github(auth=GH_AUTH)

portNumber = 0
ngrokURL = ""

def deleteWebhook( apiToken : str, ghUsername : str, repoName : str, hookID : str ) -> bool:
  """
  Deletes a webhook from a github repo. Returns
  True if the webhook was deleted successfully,
  and False otherwise.

  :param apiToken: The github personal access token
  :param ghUsername: The github username of the repo owner
  :param repoName: The name of the repo
  :param hookID: The id of the webhook to delete

  :return: True if the webhook was deleted successfully,
  """
  cmdStr = Template("""
    curl -L -fail
    -X DELETE 
    -H "Accept: application/vnd.github+json" 
    -H "Authorization: Bearer $apiToken"
    -H "X-GitHub-Api-Version: 2022-11-28" 
    https://api.github.com/repos/$ghUsername/$repoName/hooks/$hookID
  """).substitute(apiToken=apiToken, ghUsername=ghUsername, repoName=repoName, hookID=hookID).replace("\n", " ")

  out = subprocess.run(cmdStr, shell = True, capture_output=True)

  return out.returncode == 0

def createWebhook( apiToken : str, ghUsername : str, repoName : str, deliveryURL : str) -> str:
  """
  Creates a webhook for a github repo. Returns
  the id of the webhook if the webhook was created
  successfully, and an empty string otherwise.

  :param apiToken: The github personal access token
  :param ghUsername: The github username of the repo owner
  :param repoName: The name of the repo
  :param deliveryURL: The URL to deliver the webhook to

  :return: The id of the webhook if the webhook was created
  successfully, and an empty string otherwise.
  """
  
  cmdStr = Template("""
    curl -L --fail
    -X POST 
    -H "Accept: application/vnd.github+json" 
    -H "Authorization: Bearer $apiToken"
    -H "X-GitHub-Api-Version: 2022-11-28" 
    https://api.github.com/repos/$ghUsername/$repoName/hooks 
    -d '{"name":"web","active":true,"events":["push", "create", "delete"],"config":{"url": "$deliveryURL" ,"content_type":"json","insecure_ssl":"0"}}'
   """).substitute(apiToken=apiToken, ghUsername=ghUsername, repoName=repoName, deliveryURL=deliveryURL).replace("\n", " ")
                    
  out = subprocess.run(cmdStr, shell=True, capture_output=True)
  
  if out.returncode != 0:
    return ""
  else:
    return str(json.loads(out.stdout.decode("utf-8"))["id"])

if __name__ == "__main__":
  # First, run builds
  autobuilder = buildUtils.Autobuilder()
  autobuilder.initialBuild()
  
  # First, spin up the webhook listener
  listener = subprocess.Popen(["poetry", "run", "gunicorn", "-w", "1", "webhookListener:app", "-b", "localhost:" + str(portNumber)])

  # Get a random port number; we'll use this
  # later to create a connection
  portNumber += random.randint(1000, 20000)
  tunnel = ngrok.connect(portNumber)

  # Get the URL
  ngrokURL += tunnel.public_url

  # Now, load the webhook config, if it exists,
  # and delete the old webhook
  if GITHUB_WEBHOOK_ID_JSON_FNAME in os.listdir("."):
    webhook_json_s = ""
    with open(GITHUB_WEBHOOK_ID_JSON_FNAME) as f:
      webhook_json_s += f.read()
    webhook_json = json.loads(webhook_json_s)

    # Get the webhook id
    webhook_id = webhook_json["id"]

    # Delete, and assert it succeeds
    assert deleteWebhook(GITHUB_PERSONAL_ACCESS_TOKEN, GH_USERNAME, GH_REPO_NAME, webhook_id)
  
    # Delete the file
    os.remove( GITHUB_WEBHOOK_ID_JSON_FNAME )
  
  # Now, make a new webhook
  newID = createWebhook(GITHUB_PERSONAL_ACCESS_TOKEN, GH_USERNAME, GH_REPO_NAME, ngrokURL)

  # Only continue if id != ""
  assert newID != ""

  # Write the new webhook id to the file
  with open(GITHUB_WEBHOOK_ID_JSON_FNAME, "w") as f:
    f.write(json.dumps({"id": newID}))
  
  # Join the listener to keep running
  listener.wait()