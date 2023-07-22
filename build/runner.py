# This script runs the entire
# build process
from datetime import datetime, timezone, timedelta
import time

import networkx as nx

import encrypt
import buildConfig
import githubAPI
import taskgraph

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

  print(f"Waiting {secondsBetweenBuilds} seconds between builds...")
  
  # Testing: Creating a branch object, and adding it to the task
    # graph
  branch = taskgraph.Branch("develop", "uncloned", "deployed")
  taskgraph.taskGraph.addItem(branch)

  print(taskgraph.taskGraph._graph.nodes())
  print(taskgraph.taskGraph._graph.edges())

  taskgraph.taskGraph.fixItems()

  # While loop for builds:
  while True:
    break
    # Get start time, and compute earliest end time
    startTime = datetime.now(timezone.utc)
    endTime = startTime + timedelta(seconds=secondsBetweenBuilds)

    # Get the remote branches and SHA hashes
    remoteBranchesAndSHA = githubHandle.getRemoteBranchesAndSHA()
    print(remoteBranchesAndSHA)

    # # Ensure we have waited long enough
    # currTime = datetime.now(timezone.utc)
    # if currTime < endTime:
    #   time.sleep((endTime - currTime).total_seconds())