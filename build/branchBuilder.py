import os
import subprocess
from datetime import datetime, timedelta, timezone
import time
import json
import signal
import sys

import git
from jinja2 import FileSystemLoader, Environment

JSON_CONFIG = "buildConfig.json"

def buildCompleteDomainName(branchName : str, productionBranchName : str, domainName : str):
  return ( f"{branchName}." if branchName != productionBranchName else ""  ) + domainName

def wait(fastPollsTill : datetime):
  currTime = datetime.now(tz=timezone.utc)

  if currTime < fastPollsTill:
    time.sleep(10)
  else:
    time.sleep(60)


# On sigint, exit
def exitHandler(sig, frame):
  print("EXITING!!!")
  sys.exit(0)

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

  # Set signal handler for ctrl + c
  signal.signal(signal.SIGINT, exitHandler)

  while True:
    # Get the current config
    configS = ""
    with open("buildConfig.json") as f:
      configS += f.read()
    configO = json.loads(configS)

    prodBranchName = configO["production_branch"]
  
    # Reset to the correct upstream commit    
    branchName = os.path.basename(os.path.dirname(os.getcwd()))
    os.system(f"git fetch --all; git reset --hard origin/{branchName}")

    # Check if the hash has changed; if not, continue
    repo = git.Repo("..")
    currBranch = [ b for b in repo.heads if b.name == branchName ][0]
    currCommit = currBranch.commit
    currHash = currCommit.hexsha

    if currHash == prevGitHash:
      wait(fastPollsTill)
      continue
    else:
      fastPollsTill = datetime.now(tz=timezone.utc) + timedelta(minutes=1)

    # If hash is different, we need to run the build process

    # First, run the docker command to build this clone of the site
    os.system("cd ../docker; sudo ./SingleBuild.sh")
    
    # At this point, all we need to do is copy the
    # build to the right place
    for domainName in configO["domain_names"]:
      completeDName = buildCompleteDomainName(branchName, prodBranchName, domainName)
      # If domain name is already in the dir, delete it
      if completeDName in os.listdir("/var/www"):
        os.system(f"sudo rm -rf /var/www/{completeDName}")

      # Make dir
      os.system(f"sudo mkdir -p /var/www/{completeDName}")

      # Copy
      os.system(f"sudo cp -r ../site/build /var/www/{completeDName}/html")

      # Done in this domain

    # Update hash
    prevGitHash = currHash

    # Now, wait for the appropriate amount of time
    wait(fastPollsTill)
