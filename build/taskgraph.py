# This module defines the entire task graph
# for deployment.

# One possible path is when a new
# branch is made on the remote:

# uncloned: The branch is detected,
# but is not cloned yet.
# *clone*
# cloned: The branch is cloned,
# but not built yet.
# *build*
# built: The branch is built,
# but not deployed yet.
# *deploy*
# deployed: The branch is deployed,
# and this is a terminal state.
import os
import subprocess

import git
import pythongraphrunner
from pythongraphrunner import ItemBase

import buildConfig

BRANCH_DIR = "branches"

class Branch(ItemBase):
  """
  This class represents a branch
  that we're managing. It inherits
  from ItemBase, and is the main
  subject of the task graph
  """
  def __init__(self, branchName : str, currState : str, terminalState : str):
    """
    :param branchName: The name of the branch
    :param currState: The current state of the branch
    :param terminalState: The terminal state of the branch
    """
    super().__init__(currState, terminalState, branchName)
    self.branchName = branchName
  
  def buildCompleteDomainName(self, domainName : str, prodBranchName : str):
    return ( f"{self.branchName}." if self.branchName != prodBranchName else ""  ) + domainName


# First, define the clone task
def cloneTask(branch : Branch) -> str:
  """
  This task clones the branch,
  and should return the state 'cloned'
  """

  # First, make sure that the branch
  # is not yet cloned. If it is,
  # delete it
  if branch.branchName in os.listdir(BRANCH_DIR):
    subprocess.run(["rm", "-rf", os.path.join(BRANCH_DIR, branch.branchName)])

  # Get the current remote url
  repo = git.Repo("..")
  remoteURL = repo.remotes.origin.url
  
  # Now, clone it
  subprocess.run(["git", "clone", "-b", branch.branchName, "--single-branch", remoteURL, branch.branchName], cwd=BRANCH_DIR)

  # We're done! Transition to the cloned state
  return "cloned"

# Now, define the actual TaskEdge
# for cloning
cloneEdge : pythongraphrunner.TaskEdge[Branch] = pythongraphrunner.TaskEdge(["uncloned"], ["cloned"], [], cloneTask)

# Now, an edge that goes from cloned/cleaned to built. This
# builds the site
def buildTask(branch : Branch) -> str:
  """
  This task builds the site,
  and should return the state 'built'
  """
  # First, get the pwd of the docker
  # build script
  dockerBuildScriptDir = subprocess.run("cd docker; pwd", capture_output=True, shell=True, cwd=os.path.join(BRANCH_DIR, branch.branchName)).stdout.decode().strip()

  # Now, run the docker build script
  subprocess.run(["sudo", "./SingleBuild.sh"], cwd=dockerBuildScriptDir, capture_output=True)

  # Perfect, now return the built state
  return "built"

# Now, define the actual TaskEdge
# for building
buildEdge : pythongraphrunner.TaskEdge[Branch] = pythongraphrunner.TaskEdge(["cloned"], ["built"], [], buildTask)

# Now, and edge that goes from built to deployed. This
# deploys the site
def deployTask(branch : Branch) -> str:
  """
  This task deploys the site,
  and should return the state 'deployed'
  """
  # First, get the build config
  buildConfigObj = buildConfig.BuildConfig(buildConfig.BUILD_CONFIG_FNAME)

  # Now, get the domain names
  domainNames = buildConfigObj.domainNames

  # Now, get the production branch name
  productionBranchName = buildConfigObj.productionBranch

  # For each domain name, deploy
  for domain in domainNames:
    completeDomainName = branch.buildCompleteDomainName(domain, productionBranchName)

    # Delete the old site from the nginx
    # serving dir, if applicable
    subprocess.run(["sudo", "rm", "-rf", f"{buildConfig.NGINX_SITE_SERVING_DIR}/{completeDomainName}"])

    # Make a new dir, and copy the build
    # to it
    subprocess.run(["sudo", "mkdir", "-p", f"{buildConfig.NGINX_SITE_SERVING_DIR}/{completeDomainName}/html"])
    subprocess.run(f"sudo cp -r site/build/** {buildConfig.NGINX_SITE_SERVING_DIR}/{completeDomainName}/html", cwd=f"{BRANCH_DIR}/{branch.branchName}", shell=True)

  # Perfect, now return the built state
  return "deployed"

# Now, define the actual TaskEdge
# for deploying
deployEdge : pythongraphrunner.TaskEdge[Branch] = pythongraphrunner.TaskEdge(["built"], ["deployed"], [], deployTask)

# Now, add to the task graph
taskGraph : pythongraphrunner.TaskGraph[Branch] = pythongraphrunner.TaskGraph()
taskGraph.addStates( ["uncloned", "cloned", "built", "deployed"] )
taskGraph.addEdges([cloneEdge, buildEdge, deployEdge])