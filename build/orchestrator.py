# This script is responsible for orchestrating
# all the branch specific build scripts. Namely,
# this creates clones when new branches are
# made, and deletes braches that should no longer
# exist, when they are deleted on the remote
import time
import os
import subprocess
import signal
import sys

import git 

# This is a mapping from
# branch name to a popen
# instance. Allows the orchestrator
# to kill any background processes
# that are in deleted directories.
bgThreads = {}

# Handle the ctrl + c signal
def exitHandler(sig, frame):
  # Clear the bgThreads
  for branch, thread in bgThreads.items():
    thread.kill()
    # Send kill signal
    # os.killpg(os.getpgid(thread.pid), signal.SIGKILL)
    #os.kill(os.getpgid(thread.pid), signal.SIGTERM)
  
  # Exit
  sys.exit(0)
    
if __name__ == "__main__":
    # Set the signal handler
    # for ctrl + c
    signal.signal(signal.SIGINT, exitHandler)

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

      # Statup any branch builders for folders that are already
      # cloned
      for branchNameToRun in ( names.union(currBranchNames) ):
        if branchNameToRun not in bgThreads:
          # Start a bg thread that runs the corresponding
          # script
          os.chdir(os.path.abspath(os.path.expanduser(f'branches/{branchNameToRun}/build')))
          bgThreads[branchNameToRun] = subprocess.Popen(f"python3 branchBuilder.py".split())
          os.chdir(os.path.abspath(os.path.expanduser('../../../')))
        

      # Create branch folders that are needed
      remoteURL = origin.url
      for branchNameToCreate in ( names - currBranchNames ):
        # Clone the repo into that dir
        os.system(f"git clone --single-branch --branch {branchNameToCreate} {remoteURL} branches/{branchNameToCreate}")

        # Start a bg thread that runs the corresponding
        # script
        os.chdir(os.path.abspath(os.path.expanduser(f'branches/{branchNameToRun}/build')))
        bgThreads[branchNameToCreate] = subprocess.Popen(f"python3 branchBuilder.py".split())
        os.chdir(os.path.abspath(os.path.expanduser('../../../')))

      # This script runs forever,
      # so just sleep for 60 seconds
      # after completion
      time.sleep(60)
