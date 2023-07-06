"""
This file defines a runner
that runs the autobuild
script on each branch
in the repo. This allows
parrallelization of the
build process, with each branch
being independent, allowing
faster builds.

This script checks
the git repo for updates,
and if there are updates,
it runs the autobuild
script in a cloned version
of the repo. This allows
the autobuild script to
run in parallel on each
branch, and also
allows the autobuild
to use incremental
builds, which are
faster than full
builds.
"""
import os
import random
import json
from datetime import datetime

import git
import schedule

from data import DB, Config, DB_FNAME

class Deployment:
    """
    Represents one deployment of the site. Provides
    convenience methods for building and deploying
    the site in one function, and can schedule
    subsequent builds and deployments.
    """
    def __init__(self, branchName : str, domainName : str, db : DB):
        self.branchName = branchName
        self.domainName = domainName
        self.db = db

        # Store the hash of the last commit
        # that was built
        self.lastCommitHash = None

        repo = git.Repo("..")
        branch = repo.branches[self.branchName]
        self.lastCommitHash = branch.commit.hexsha
    
    def _build(self):
        """
        Runs the build process
        for this deployment.
        """

        # First, get the folder name
        # for the branch
        folderName = self.db.getBranchFolderName(self.branchName)

        # Now, go to that folder, and run the autobuild script
        # with the desired branch name
        os.system(f"cd ../{folderName}; python3 autobuild.py {self.branchName}")
    
    def buildTask(self):
        """
        This function internally runs the build process for this
        deployment, updates the DB with the new update time,
        and schedules the next build task; it keeps track of
        whether or not the build is a changing build, and
        schedules the next build task accordingly.
        """
        # First, check if we have a new commit on this
        # branch
        os.system("git fetch")
        repo = git.Repo("..")
        branch = repo.branches[self.branchName]

        # If the commit hash is the same, we don't
        # need to build
        if branch.commit.hexsha == self.lastCommitHash:
            # In this case, if the last build was
            # more than 5 minutes ago, we need
            # to make this build a non-changing
            # build
            if ( datetime.utcnow() - self.db.getBranchUpdateTime(self.branchName) ).total_seconds() > 300:
                # Make non changing build
                self.db.setBranchNotChanging(self.branchName)
        else:
            # Build, make the build changing, and update
            # the last commit hash
            self._build()
            self.db.setBranchChanging(self.branchName)
            self.lastCommitHash = branch.commit.hexsha
            self.db.updateTime(self.branchName)
        
        # Now, schedule the next build task
        # based on whether or not this build
        # is changing
        if self.db.getBranchChanging(self.branchName):
            schedule.every(5).seconds.do(self.buildTask)
        else:
            schedule.every(1).minutes.do(self.buildTask)

if __name__ == "__main__":
    # First, run a git fetch and pull

    # TODO: Use the production brach
    # as the base branch for the
    # autobuild
    os.system("git fetch")

    # Make a DB against the
    # desired file name; pulls
    # old data if applicable
    db = DB(DB_FNAME)

    # Make a config object
    config = Config("build.conf")

    # Get the repo url to pull from
    repo_url = config.get("repo_url")

    # Get the branch names from the git repo
    repo = git.Repo("..")
    branchNames = [branch.name for branch in repo.branches]
    
    # First, create new branches that we need in the DB
    for branchName in branchNames:
        if branchName not in db.getBranchNames():
            # Generate a new branch name
            # for the branch
            folderName = "sphinxbuild_" + str(random.randint(0, 1000000000))

            # Create the branch
            os.system(f"cd ..; mkdir -p {folderName}; cd {folderName}; git clone {repo_url} .")

            # Add the branch to the DB
            db.createBranch(branchName, folderName)

    # Now, delete branches that are in the DB, but not
    # in the git repo
    for branchName in db.getBranchNames():
        if branchName not in branchNames:
            # Delete the branch
            os.system(f"cd ..; rm -rf {db.getBranchFolderName(branchName)}")

            # Remove the branch from the DB
            db.removeBranch(branchName)
    
    # At this point, we can start queing up
    # autobuilds for each branch; once
    # an autobuild is complete,
    # it needs to schedule another
    # build, which is timed base on whether
    # or not it's a changing build. This
    # can be handled nicely by invoking
    # a member function on a deployment
    # class