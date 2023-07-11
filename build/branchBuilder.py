import os
import subprocess
from datetime import datetime, timedelta, timezone
import time
import json

import git
from jinja2 import FileSystemLoader, Environment

JSON_CONFIG = "buildConfig.json"

def buildCompleteDomainName(branchName : str, productionBranchName : str):
  return ( f"{branchName}." if branchName != productionBranchName else ""  ) + domainName

def makeNginxConfig(branchName : str, domainName : str, productionBranchName : str):
  # Use jinja to generate the
  # nginx configuration file
  # for this site
  TEMPLATE_FILE = "nginxTemplate.conf"
  loader = FileSystemLoader(searchpath="./")

  completeDomainName = buildCompleteDomainName(branchName, productionBranchName)

  # Here is the context we use
  # to generate the nginx
  # configuration text
  context = {
     "SITE_HTML_DIR" : f"/var/www/{completeDomainName}",
     "COMPLETE_DOMAIN_NAME" : completeDomainName
  }

  # Now, render and return
  template = Environment(loader=loader).get_template(TEMPLATE_FILE)
  return template.render(context)

def wait(fastPollsTill : datetime):
  currTime = datetime.now(tz=timezone.utc)

  if currTime < fastPollsTill:
    time.sleep(5)
  else:
    time.sleep(60)

if __name__ == "__main__":
  # When ran by itself, this script
  # runs a simple build process to
  # pull new changes, and build +
  # deploy the site as changes are
  # being made.

  # This variable stores a datetime that is
  # the datetime where we  are going to polling
  # at a higher speed till; i.e. if the current
  # datetime < the following, we poll fast,
  # otherwise we don't. If we keep setting
  # this to 1 minute after the last
  # new commit, this is an easy way to keep track
  # of this flag
  fastPollsTill : datetime = datetime.now(tz=timezone.utc) - timedelta(seconds=1)
  prevGitHash = "" 

  while True:
    # Get the current config
    configS = ""
    with open("buildConfig.json") as f:
      configS += f.read()
    configO = json.loads(configS)

    prodBranchName = configO["production_branch"]
  
    # Checkout the correct branch, and pull. This
    # is based on the current branch name
    branchName = os.path.basename(os.getcwd())
    os.system(f"git checkout -B {branchName}; git pull -f origin {branchName}")

    # Check if the hash has changed; if not, continue
    repo = git.Repo("..")
    currBranch = [ b for b in repo.heads if b.name == branchName ][0]
    currCommit = currBranch.commit
    currHash = currCommit.hexsha

    if currHash == prevGitHash:
      wait(fastPollsTill)
    else:
      fastPollsTill = datetime.now(tz=timezone.utc) + timedelta(minutes=1)

    # If hash is different, we need to run the build process

    # First, run the docker command to build this clone of the site
    os.system("cd ../docker; ./SingleBuild.sh")
    
    # At this point, all we need to do is copy the
    # build to the right place
    for domainName in configO["domain_names"]:
      # If domain name is already in the dir, delete it
      if buildCompleteDomainName(domainName, prodBranchName) in os.listdir("/var/www"):
        os.system(f"rm -rf /var/www/{buildCompleteDomainName(domainName, prodBranchName)}")

      # Copy
      os.system(f"cp -r ../site/build /var/www/{buildCompleteDomainName(domainName, prodBranchName)}")    
      # Done in this domain

    # Update hash
    prevGitHash = currHash

    # Now, wait for the appropriate amount of time
    if datetime.now(tz=timezone.utc) < fastPollsTill:
      time.sleep(5)
    else:
      time.sleep(60)
