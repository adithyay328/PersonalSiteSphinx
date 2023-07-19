# Script containing all logic for automated
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
BRANCH_FETCH_INTERVAl_SECONDS : int = 180

NON_ACTIVE_CHECK_INTERVAL_SECONDS : int = 60 # How often to check for updates if a branch is not active
ACTIVE_CHECK_INTERVAL_SECONDS : int = 30 # How often to check for updates if a branch is being actively changed
ACTIVE_DURATION_SECONDS : int = 20 # How long a branch is considered "active" after a change

MINIMUM_TIME_BETWEEN_RUNS = 10 # Minimum time to wait between build runs. Helps with respecting rate limits

BRANCH_DIR : str = "branches"
REMOTE_NAME : str = "origin"
NGINX_SITES_AVAILABLE_DIR : str = "/etc/nginx/sites-available"
NGINX_SITES_ENABLED_DIR : str = "/etc/nginx/sites-enabled"
NGINX_SITE_SERVING_DIR : str = "/var/www"
CONFIG_FILE_NAME : str = "buildConfig.json"

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

class BranchBuilder:
  def __init__(self, branchDir : str, domainNames : List[str], productionBranchName : str):
    self.branchDir = branchDir
    self.domainNames = domainNames
    self.productionBranchName = productionBranchName

    self.branchName = branchDir.split("/")[-1]

    # Keeping track of the current commit hash
    # to know if we need to rebuild
    self.hash = ""

    # Keeping track of the last time we
    # rebuilt the branch
    self.lastBuildTime = datetime.datetime.now(tz=datetime.timezone.utc)

  def buildCompleteDomainName(self, domainName : str):
    return ( f"{self.branchName}." if self.branchName != self.productionBranchName else ""  ) + domainName

  def needsRebuild(self):
    """
    Checks git to see if the current
    branch needs to be rebuilt; i.e.
    if the current commit's hash
    matches remote's head.
    """
    # First, update info
    # about the remote
    updateGit(self.branchDir, REMOTE_NAME, True)

    # Now, get the current commit hash
    result = subprocess.run(["git", "show", "--pretty=format:%H", "--no-patch"], capture_output=True, cwd=self.branchDir)
    currentHash = result.stdout.decode().strip()

    return currentHash != self.hash
  
  def build(self):
    """
    Runs the full build process,
    and updates the current
    commit hash
    """
    # First, get the directory of the docker
    # build script we need to run
    dockerBuildScriptDir = subprocess.run("cd docker; pwd", capture_output=True, shell=True, cwd=self.branchDir).stdout.decode().strip()

    # Now, run the docker build script
    subprocess.run(["sudo", "./SingleBuild.sh"], cwd=dockerBuildScriptDir, capture_output=True)

    # Now, update the current commit hash
    result = subprocess.run(["git", "show", "--pretty=format:%H", "--no-patch"], capture_output=True, cwd=self.branchDir)
    self.hash = result.stdout.decode().strip()

    # Now, copy the build to the correct
    # nginx serving directory
    for domain in self.domainNames:
      # First, compute the full domain name
      fullDomain = self.buildCompleteDomainName(domain)

      # First, delete the old directory
      # if it exists
      subprocess.run(["sudo", "rm", "-rf", f"{NGINX_SITE_SERVING_DIR}/{fullDomain}"], capture_output=True)

      # Now, make a new directory
      subprocess.run(["sudo", "mkdir", "-p", f"{NGINX_SITE_SERVING_DIR}/{fullDomain}"], capture_output=True)

      # Now, copy the build to the new directory
      subprocess.run(["sudo", "cp", "-r", f"site/build", f"{NGINX_SITE_SERVING_DIR}/{fullDomain}"], cwd=self.branchDir, capture_output=True)

      # Done!
    
  def autobuildLoop(self, endDatetime : datetime.datetime):
    """
    This function runs the full loop
    of the autobuild, which involves
    checking if the branch needs to
    be rebuilt, and if so, rebuilding
    it, and then sleeping for the appropraite
    amount of time.

    This function will try to end
    at the specified end datetime,
    but may end later if the branch
    build is still running.
    """
    # Set thread niceness to be lower
    lowerPriority()

    while datetime.datetime.now(tz=datetime.timezone.utc) < endDatetime:
      # First, check if we need to rebuild
      if self.needsRebuild():
        # If so, rebuild and set the
        # last build time
        self.build()
        self.lastBuildTime = datetime.datetime.now(tz=datetime.timezone.utc)
      
      # Now, sleep for the appropriate amount of time
      if datetime.datetime.now(tz=datetime.timezone.utc) - self.lastBuildTime < datetime.timedelta(seconds=ACTIVE_DURATION_SECONDS):
        # In this case, the branch is active; sleep for the active duration,
        # unless that is past the end datetime, in which case we return
        targetedWakeTime = datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(seconds=ACTIVE_CHECK_INTERVAL_SECONDS)
        if targetedWakeTime > endDatetime:
          return
        else:
          time.sleep(ACTIVE_CHECK_INTERVAL_SECONDS)
      else:
        # In this case, we're not in the active state. Compute
        # targeted wake time, and if it's too late, exit
        targetedWakeTime = datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(seconds=NON_ACTIVE_CHECK_INTERVAL_SECONDS)
        if targetedWakeTime > endDatetime:
          return
        else:
          time.sleep(NON_ACTIVE_CHECK_INTERVAL_SECONDS)

class Autobuilder:
  def __init__(self):
    # Lists off all branches
    # currently on the current machine.
    # These are the branches that will
    # be built during the build process
    self.existingBranches : List[str] = getFolderNames(BRANCH_DIR)

    # A ap from branch name to BranchBuilder
    self.branchBuilders : Dict[str, BranchBuilder] = {}
    
    # A map from branch name to commit hash
    self.branchToHash : Dict[str, str] = {}

  def update(self):
    """
    Every time this method is called,
    it updates the current repo,
    and creates any new branches
    that are needed, while removing
    branches that are no longer
    on the remote. After this, all
    branches that still exist
    will be built and pushed
    to deployment
    """
    # First, update the current repo
    updateGit(".", REMOTE_NAME, False)

    # Now, get all branch names
    branchNames = set(getBranchNames(".", REMOTE_NAME))

    # This is a list of all the popen objects we created.
    # Wait for all of them to finish
    processes = []

    # Now, we need to update the branches we currently
    # maintain. First, remove any branches that no longer
    # exist
    priorBranches = set(self.existingBranches)
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
    remoteURL = subprocess.run(["git", "remote", "get-url", REMOTE_NAME], capture_output=True).stdout.decode().strip()
    for branchNameToCreate in branchNames - priorBranches:
      # Create the dir
      processes.append(
        subprocess.Popen(
          ["git", "clone", "--branch", branchNameToCreate, "--single-branch", remoteURL, f"{branchNameToCreate}"],
          stdout=subprocess.DEVNULL,
          stderr=subprocess.DEVNULL
        , cwd=BRANCH_DIR)
      )

      # Add to the dict of branch builders
      self.branchBuilders[branchNameToCreate] = BranchBuilder(f"{BRANCH_DIR}/{branchNameToCreate}", DOMAIN_NAMES, PRODUCTION_BRANCH_NAME)
    
    # Now, create branch builders for all branches that already existed
    # but were not in the dict of branch builders
    for branchName in branchNames.union(priorBranches):
      if branchName not in self.branchBuilders:
        self.branchBuilders[branchName] = BranchBuilder(f"{BRANCH_DIR}/{branchName}", DOMAIN_NAMES, PRODUCTION_BRANCH_NAME)
    
    # Wait for all processes to finish
    for process in processes:
      process.wait()
    # At this point, all needed branches are on the machine. Now we can do our builds
    # for the next BRANCH_FETCH_INTERVAl_SECONDS seconds
  
  def runBuilders(self):
    """
    This function runs the builders
    for all branches that exist, and
    schedules re-fetching
    of branches from the repo.
    """
    # First, update the list of
    # branches
    self.update()

    # Now, run all the builders
    # in different threads
    endDatetime = datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(seconds=BRANCH_FETCH_INTERVAl_SECONDS)
    processes = []

    for branchName, branchBuilder in self.branchBuilders.items():
      processes.append(
        threading.Thread(
          target=branchBuilder.autobuildLoop,
          args=(endDatetime,)
        )
      )

      # Start the thread
      processes[-1].start()
    
    # Wait for all threads to finish
    for process in processes:
      process.join()
        
    # if the threads exited early,
    # wait for the rest of the time
    # before returning
    if datetime.datetime.now(tz=datetime.timezone.utc) < endDatetime:
      time.sleep((endDatetime - datetime.datetime.now(tz=datetime.timezone.utc)).total_seconds())

  def run(self):
    # This loop runs repeatedly. It sleeps internally
    # to limit the max run rate, and after cloning
    # the correct branches, runs builds on branches
    # with new hashes

    # We use this to limit run rate
    startTime = datetime.datetime.now(tz=datetime.timezone.utc)

    # First, get a list of all branches.
    branchNames = getBranchNames(".", REMOTE_NAME)
    
    # Check if branch names is same as current list of
    # branches
    currClonedBranches = getFolderNames(BRANCH_DIR)

    # If not equal, update branches
    if set(branchNames) != set(currClonedBranches):
      update()

    # Now, get hashes for all branches. If not
    # the same as the built hashes, re-build
    for branchName in branchNames:
      
    
    
    
if __name__ == "__main__":
  autobuilder = Autobuilder()

  # Set lower process priority
  p = psutil.Process(os.getpid())
  p.nice(19)

  while True:
    autobuilder.runBuilders()
