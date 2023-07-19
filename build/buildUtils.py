# Contains utils for building the site, and
# doing other operations# Script containing all logic for automated
# builds

import os
from typing import List, Dict
import subprocess
import json
import threading
import datetime
import time
import psutil

"""CONTANTS AND CONFIG:"""
BRANCH_DIR : str = "branches"
REMOTE_NAME : str = "origin"
NGINX_SITES_AVAILABLE_DIR : str = "/etc/nginx/sites-available"
NGINX_SITES_ENABLED_DIR : str = "/etc/nginx/sites-enabled"
NGINX_SITE_SERVING_DIR : str = "/var/www"
CONFIG_FILE_NAME : str = "buildConfig.json"

BRANCH_HASH_JSON_DIR = "branchHashes.json"

CONFIG_OBJ = {}
with open(CONFIG_FILE_NAME) as f:
  CONFIG_OBJ.update(json.loads(f.read()))
PRODUCTION_BRANCH_NAME : str = CONFIG_OBJ["production_branch"]
DOMAIN_NAMES : List[str] = CONFIG_OBJ["domain_names"]


def getFolderNames(path: str) -> List[str]:
  """
  Returns a list of all folders in a
  given path
  """
  folders = []
  
  # Ignore if not a directory
  if not os.path.isdir(path):
    return []
  
  for entry in os.scandir(path):
    if entry.is_dir():
      folders.append(entry.name)
  
  return folders

def updateGit(path : str, remote : str, reset : bool) -> None:
  """
  Given a directory, updates the git
  repo in that directory by fetching
  all remote branches, and pushing
  the current commit up to the 
  latest commit
  """
  # First, run git fetch --all -p . to get the latest
  # branches
  subprocess.run(["git", "fetch", "--all", "-p"], cwd=path, capture_output=True)

  # Now, get the current git branch
  result = subprocess.run(["git", "branch", "--show-current"], cwd=path, capture_output=True)
  branchName = result.stdout.decode().strip()

  # Now, reset to the head of the remote if asked
  if reset:
    subprocess.run(["git", "reset", "--hard", f"{remote}/{branchName}"], capture_output=True, cwd=path)

def getBranchNames(path : str, remote : str) -> List[str]:
  """
  Given a directory, lists all branch names
  in the associated git repo
  """
  res = subprocess.run(["git", "ls-remote", "--heads", "--quiet", f"{remote}"], capture_output=True, cwd=path)
  lines = res.stdout.decode().split("\n")
  branches = []

  for line in lines:
    line = line.strip()
    if line == "":
      continue

    # Get the branch name
    branchName = line.split("/")[-1]
    branches.append(branchName)
  
  return branches

def lowerPriority():
  # Set lower process priority
  p = psutil.Process(os.getpid())
  p.nice(19)

def cloneBranch(branchNameToCreate : str):
  """
  Given a branch name, clones the repo
  with that branch name into the branch dir
  at the right place
  """
  remoteURL = subprocess.run(["git", "remote", "get-url", REMOTE_NAME], capture_output=True).stdout.decode().strip()
  
  # Create the dir and clone
  subprocess.run(
      ["git", "clone", "--branch", branchNameToCreate, "--single-branch", remoteURL, f"{branchNameToCreate}"],
      capture_output = True,
      cwd=BRANCH_DIR
  )

def getGitHash(branchName : str):
  """
  Given the directory of a git repo,
  returns the hash of the head commit.
  """
  return subprocess.run(["git", "show", "--pretty=format:%H", "--no-patch"], capture_output=True, cwd=f"{BRANCH_DIR}/{branchName}").stdout.decode().strip()
  

class BranchBuilder:
  def __init__(self, branchDir : str, domainNames : List[str], productionBranchName : str):
    self.branchDir = branchDir
    self.domainNames = domainNames
    self.productionBranchName = productionBranchName

    # Brach name is made lower case, since
    # domain requests are usually lower case
    self.branchName = branchDir.split("/")[-1].lower()

  def buildCompleteDomainName(self, domainName : str):
    return ( f"{self.branchName}." if self.branchName != self.productionBranchName else ""  ) + domainName

  def build(self):
    """
    Runs the full build process,
    with deployment to nginx
    """
    # First, get the directory of the docker
    # build script we need to run
    dockerBuildScriptDir = subprocess.run("cd docker; pwd", capture_output=True, shell=True, cwd=self.branchDir).stdout.decode().strip()

    # Now, run the docker build script
    subprocess.run(["sudo", "./SingleBuild.sh"], cwd=dockerBuildScriptDir, capture_output=True)

    # Now, copy the build to the correct
    # nginx serving directory
    for domain in self.domainNames:
      # First, compute the full domain name
      fullDomain = self.buildCompleteDomainName(domain)

      # First, delete the old directory
      # if it exists
      subprocess.run(["sudo", "rm", "-rf", f"{NGINX_SITE_SERVING_DIR}/{fullDomain}"], capture_output=True)

      # Now, make a new directory
      subprocess.run(["sudo", "mkdir", "-p", f"{NGINX_SITE_SERVING_DIR}/{fullDomain}/html"], capture_output=True)

      # Now, copy the build to the new directory
      subprocess.run(f"sudo cp -r site/build/** {NGINX_SITE_SERVING_DIR}/{fullDomain}/html", cwd=self.branchDir, shell=True, capture_output=True)

      # Done!

class Autobuilder:
  def __init__(self):
    # A map from branch name to BranchBuilder
    self.branchBuilders : Dict[str, BranchBuilder] = {}
    
    # A map from branch name to commit hash
    self.branchToHash : Dict[str, str] = {}

    # Loads BRANCH_HASH_JSON_DIR if available
    if BRANCH_HASH_JSON_DIR in os.listdir("."):
      with open(BRANCH_HASH_JSON_DIR) as f:
        s = f.read()
        self.branchToHash = json.loads(s)

  def initialBuild(self):
    """
    Every time this method is called,
    it updates the current repo,
    and creates any new branches
    that are needed, while removing
    branches that are no longer
    on the remote. After this, all
    branches that still exist
    will be built and pushed
    to deployment.

    This is meant to be ran once when
    the auto-build stack starts, to build
    any new branches that were made when
    the builder was turned off
    """
    # First, update the current repo
    updateGit(".", REMOTE_NAME, False)

    # Now, get all branch names
    branchNames = set(getBranchNames(".", REMOTE_NAME))

    # This is a list of all the popen objects we created.
    # Wait for all of them to finish
    processes = []

    # This is a list of all branches we need to re-build
    branchesToRebuild = []

    # Now, we need to update the branches we currently
    # maintain. First, remove any branches that no longer
    # exist
    priorBranches = set(getFolderNames(BRANCH_DIR))
    for branchNameToDelete in priorBranches - branchNames:
      # Delete the dir
      processes.append(
        subprocess.Popen(
          ["rm", "-rf", f"{branchNameToDelete}"],
          stdout=subprocess.DEVNULL,
          stderr=subprocess.DEVNULL
        , cwd=BRANCH_DIR)
      )

      # Remove from the dict of branch builders
      del self.branchBuilders[branchNameToDelete]
    
    # Now, create any new branches
    for branchNameToCreate in branchNames - priorBranches:
      cloneBranch(branchNameToCreate)

      # Add to the dict of branch builders
      self.branchBuilders[branchNameToCreate] = BranchBuilder(f"{BRANCH_DIR}/{branchNameToCreate}", DOMAIN_NAMES, PRODUCTION_BRANCH_NAME)

      # Check if we need to re-build
      if branchNameToCreate not in self.branchToHash or getGitHash(branchNameToCreate) != self.branchToHash[branchNameToCreate]:
        branchesToRebuild.append(branchNameToCreate)
    
    # Now, create branch builders for all branches that already existed
    # but were not in the dict of branch builders
    for branchName in branchNames.union(priorBranches):
      if branchName not in self.branchBuilders:
        self.branchBuilders[branchName] = BranchBuilder(f"{BRANCH_DIR}/{branchName}", DOMAIN_NAMES, PRODUCTION_BRANCH_NAME)

        # Rebuild if needed
        if branchName not in self.branchToHash or getGitHash(branchName) != self.branchToHash[branchName]:
          branchesToRebuild.append(branchName)
    
    # Wait for all processes to finish
    for process in processes:
      process.wait()

    # Now, do all builds
    for branchName in branchesToRebuild:
      # Run build
      self.branchBuilders[branchName].build()

      # Set hash
      self.branchToHash[branchName] = getGitHash(branchName)

    # Update the hash json
    if BRANCH_HASH_JSON_DIR in os.listdir("."):
      os.remove(BRANCH_HASH_JSON_DIR)
    with open(BRANCH_HASH_JSON_DIR, "w") as f:
      f.write(json.dumps(self.branchToHash))

if __name__ == "__main__":
  autobuilder = Autobuilder()
  autobuilder.initialBuild()
