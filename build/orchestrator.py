# This script is responsible for orchestrating
# all the branch specific build scripts. Namely,
# this creates clones when new branches are
# made, and deletes braches that should no longer
# exist, when they are deleted on the remote
import time
import os
import subprocess

import git 

if __name__ == "__main__":
    # This is a mapping from
    # branch name to a popen
    # instance. Allows the orchestrator
    # to kill any background processes
    # that are in deleted directories.
    bgThreads = {}
  
    while True:
      # Do a git fetch,
      # and check all branches
      # on remote
      os.system("git fetch -p")

      # Get names of all branches 
      rep = git.Repo("..")
      origin = rep.remotes.origin
      branches = [r for r in origin.refs if type(r) == git.RemoteReference]
      names = [b.name.split("/")[-1] for b in branches]  
      # Remove HEAD from names and convert into a set  
      names = set([name for name in names if name != "HEAD"])

      # Get list of branch dirs we currently have
      currBranchNames = set(os.listdir("branches"))

      # Delete branch folders that aren't needed
      # destroying any bgThreads that are in that directory
      for branchNameToDelete in ( currBranchNames - names ):
        if branchNameToDelete in bgThreads:
          bgThreads[branchNameToDelete].kill()
          del bgThreads[branchNameToDelete]

      os.system(f"rm -rf branches/{branchNameToDelete}")

      # Create branch folders that are needed
      remoteURL = origin.url
      print(remoteURL)
      for branchNameToCreate in ( names - currBranchNames ):
        # Clone the repo into that dir
        os.system(f"git clone {remoteURL} branches/{branchNameToCreate}")

        # Start a bg thread that runs the corresponding
        # script
        bgThreads[branchNameToCreate] = subprocess.Popen(f"python3 branches/{branchNameToCreate}/build/branchBuilder.py")

      # This script runs forever,
      # so just sleep for 60 seconds
      # after completion
      time.sleep(60)
