# This script runs the entire
# build process
from datetime import datetime, timezone, timedelta
import time
import json

import buildConfig
import githubAPI
import taskgraph

BRANCH_HASHES_FNAME = "branchHashes.json"

if __name__ == "__main__":
  verified_key = ""
  buildConfigObj = buildConfig.BuildConfig( buildConfig.BUILD_CONFIG_FNAME )

  while verified_key == "":
    key = input("Enter the encryption key: ")

    # Attempt to decrypt the build config;
    # if that fails then the key is wrong
    try:
      githubHandle = githubAPI.GHAPIHandle( githubAPI.GITHUB_KEY_FILE, key, buildConfigObj.repoName, buildConfigObj.repoOwnerName )

      verified_key += key
    except Exception as e:
      print("Incorrect key, or incorrect config file!")
      print(e)
      pass
  
  # Get the build config
  buildConfigObj = buildConfig.BuildConfig(buildConfig.BUILD_CONFIG_FNAME)

  # Make the github handle
  githubHandle = githubAPI.GHAPIHandle( githubAPI.GITHUB_KEY_FILE, verified_key, buildConfigObj.repoName, buildConfigObj.repoOwnerName )

  # Get the number of seconds to wait
  # between builds
  secondsBetweenBuilds = buildConfigObj.secondsBetweenBuilds

  # While loop for builds:
  while True:
    # Get start time, and compute earliest end time
    startTime = datetime.now(timezone.utc)
    endTime = startTime + timedelta(seconds=secondsBetweenBuilds)

    print(f"Waiting {secondsBetweenBuilds} seconds between builds...")

    # Get the remote branches and SHA hashes
    remoteBranchesAndSHA = githubHandle.getRemoteBranchesAndSHA()
    
    # Load the most recent branch hashes
    mostRecentBranchHashes = {}
    with open(BRANCH_HASHES_FNAME) as f:
      mostRecentBranchHashes.update(json.loads(f.read()))
    
    # Now, compare the remote branches and SHA hashes;
    # if any are different, change state to out_of_date.
    # If any are orphaned, update state to orphaned
    # and change target state to removed
    # If any new branches are found, add them to the
    # task graph with state uncloned
    for branchName, sha in remoteBranchesAndSHA.items():
      if branchName not in mostRecentBranchHashes:
        # Add the branch to the task graph
        newBranch = taskgraph.Branch(branchName, "uncloned", "deployed")
        taskgraph.taskGraph.addItem(newBranch)
      elif sha != mostRecentBranchHashes[branchName]:
        # Update the branch state to out_of_date
        taskgraph.taskGraph.updateItemStates(branchName, "out_of_date", "deployed")
    
    # Now, check for orphaned branches
    for branchName in mostRecentBranchHashes.keys():
      if branchName not in remoteBranchesAndSHA:
        # Update the branch state to orphaned
        taskgraph.taskGraph.updateItemStates(branchName, "orphaned", "removed")
      
    # Now, run the task graph
    taskgraph.taskGraph.fixItems()

    # Now, delete all branch objects that are
    # in the removed state
    for branchName in mostRecentBranchHashes.keys():
      if branchName not in remoteBranchesAndSHA:
        # Delete the branch object
        taskgraph.taskGraph.removeItem(branchName)
    
    # Now, save the most recent branch hashes
    with open(BRANCH_HASHES_FNAME, "w") as f:
      f.write(json.dumps(remoteBranchesAndSHA))

    # # Ensure we have waited long enough
    currTime = datetime.now(timezone.utc)
    if currTime < endTime:
      time.sleep((endTime - currTime).total_seconds())