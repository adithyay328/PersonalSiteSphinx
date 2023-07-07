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
import threading
import time

import git
import schedule
from jinja2 import Environment, FileSystemLoader

from data import DB, Config, DB_FNAME

class SiteVersion:
    """
    This class represents a single
    deployment of the site. This is
    a combination of a branch, which determines
    the version of the site, a domain
    name, which determines the domain
    we are going to deploy this version to,
    and a source directory, which is the
    directory that contains the source
    code for this version of the site.
    """

    def __init__(self, branchName: str, domainName: str, sourceDir: str):
        # Storing given values
        self.branchName = branchName
        self.domainName = domainName
        self.sourceDir = sourceDir

        # Compute the remaining values
        self.completeDomainName = (
            f"{branchName}." if branchName != "production" else ""
        ) + domainName
        self.directoryName = "/var/www/" + self.completeDomainName
        self.nginxConfigFileName = self.completeDomainName + ".conf"

    def _runCmdInDir(self, command: str):
        """
        Cd's to the correct directory
        for this site, and then runs
        the given command.
        """
        os.system(f"cd ../{self.sourceDir}; {command}")

    def _getNginxConfig(self) -> str:
        """
        Creates this SiteVersion's nginx
        configuration file, and returns it
        as a string
        """
        # Use jinja to generate the
        # nginx configuration file
        # for this site
        TEMPLATE_FILE = "nginxTemplate.conf"

        loader = FileSystemLoader(searchpath="./")

        # Here is the context we use
        # to generate the nginx
        # configuration text
        context = {
            "SITE_HTML_DIR": self.directoryName,
            "COMPLETE_DOMAIN_NAME": self.completeDomainName,
        }

        # Now, render and return
        template = Environment(loader=loader).get_template(TEMPLATE_FILE)
        return template.render(context)

    def _writeNginxConfig(self) -> None:
        """
        Generates and then writes this site's
        nginx config to the nginx config dir.
        """

        # First, if the config file is in
        # the sites-enabled directory, we
        # need to delete that link and
        # delete the nginx file in sites-available
        if self.nginxConfigFileName in os.listdir("/etc/nginx/sites-available"):
            self._runCmdInDir(
                "sudo rm /etc/nginx/sites-enabled/" + self.nginxConfigFileName
            )
            self._runCmdInDir(
                "sudo rm /etc/nginx/sites-available/" + self.nginxConfigFileName
            )

        NEW_NGINX_SITES_AVAILABLE_FILENAME = (
            "/etc/nginx/sites-available/" + self.nginxConfigFileName
        )
        NEW_NGINX_SITES_ENABLED_FILENAME = (
            "/etc/nginx/sites-enabled/" + self.nginxConfigFileName
        )

        # Now, write the nginx config file via a proxy
        # file, since open can't use root.

        # Generate a random filename
        TEMP_FILENAME = str(random.randint(0, 10000)) + "temp.conf"
        if os.path.exists(TEMP_FILENAME):
            os.remove(TEMP_FILENAME)

        with open(TEMP_FILENAME, "w") as nginxConfigFile:
            nginxConfigFile.write(self._getNginxConfig())

        # Now, copy the file to the correct
        # location
        os.system(f"sudo cp {TEMP_FILENAME} {NEW_NGINX_SITES_AVAILABLE_FILENAME}")

        os.remove(TEMP_FILENAME)

        # Now, create a link to the
        # nginx config file in the
        # sites-enabled directory
        os.system(
            f"sudo ln -s {NEW_NGINX_SITES_AVAILABLE_FILENAME} {NEW_NGINX_SITES_ENABLED_FILENAME}"
        )

        # Done!
    
    def _build(self) -> None:
        """
        Runs the build script for this version
        of the site, and leaves it in the
        build directory of the source dir.
        """
        self._runCmdInDir("cd docker && sudo ./SingleBuild.sh")
    
    def _copyBuild(self) -> None:
        """
        Copies the current build to the correct
        directory for this version of the site
        """
        # Delete the old build, if it exists
        if os.path.exists(self.directoryName):
            os.system(f"sudo rm -rf {self.directoryName}")
        
        # Now, copy the build to the
        # correct directory, after making
        # sure that the directory exists
        self._runCmdInDir(f"sudo mkdir -p {self.directoryName}/html")
        self._runCmdInDir(f"sudo cp -r site/build/* {self.directoryName}/html")

    def buildAndDeploy(self) -> None:
        """
        This function
        a) updates nginx conf
        b) builds the site
        c) copies the build to the correct
        directory
        """
        self._writeNginxConfig()
        self._build()
        self._copyBuild()

        # Reload nginx
        assert os.system("sudo systemctl restart nginx.service") == 0
    
    def destroySite(self) -> None:
        """
        Destroys this site, removing
        the build otuputs and the nginx
        config for this site.
        """

        # First, remove the nginx
        # config file
        self._runCmdInDir(
            "sudo rm /etc/nginx/sites-available/" + self.nginxConfigFileName
        )
        self._runCmdInDir(
            "sudo rm /etc/nginx/sites-enabled/" + self.nginxConfigFileName
        )

        # Now, remove the build directory
        self._runCmdInDir(f"sudo rm -rf {self.directoryName}")

        # Done!

class Runner:
    """
    Class whose instance represents a runner
    that runs all auto-build and update logic.
    """

    def __init__(self, db: DB, config: Config):
        self.db = db
        self.config = config

        # Get the list of domains from the config
        self.domains = self.config.get("site_names")

        # Get the branch names and hashes from the
        # database
        self.branchNames = self.db.getBranchNames()

        # Create a dict from branch name to
        # hash
        self.branchHashes = {}
        for branchName in self.branchNames:
            self.branchHashes[branchName] = db.getBranchHash(branchName)

        # A flag indicating whether we're elevated
        # or not
        self.elevated = False
        self.elevatedTime = datetime.utcnow()

    def _runBuildForBranch(self, branchName: str):
        """
        Builds a branch and does all deployment
        work for it
        """
        # The one common thing we need is
        # to build the site
        site = SiteVersion(branchName, self.domains[0], self.db.getBranchFolderName(branchName))
        site._build()

        for domain in self.domains:
            # For all other domains, overwrite
            # nginx config and copy build
            version = SiteVersion(
                branchName, domain, self.db.getBranchFolderName(branchName)
            )

            version._writeNginxConfig()
            version._copyBuild()
        
        # Done!

    def _runBuilds(self):
        """
        Runs builds to update the site.
        """
        # Update the branch names and hashes
        self.branchNames = self.db.getBranchNames()

        # Create a dict from branch name to
        # hash
        self.branchHashes = {}
        for branchName in self.branchNames:
            self.branchHashes[branchName] = db.getBranchHash(branchName)


        # First, do a git pull and get a mapping
        # from branch name to hash
        os.system("git fetch")
        repo = git.Repo("..")
        branchNames = [branch.name for branch in repo.branches]
        mapping = {}

        for branchName in branchNames:
            branch = repo.branches[branchName]
            mapping[branchName] = branch.commit.hexsha
        
        # We keep a list of build threads
        # that are running
        buildThreads = []

        # Now, iterate through; if a new branch exists,
        # create it and build. If a branch has been deleted,
        # delete it. If a branch has been updated, build it.

        # If a branch has been added or changed,
        # set the flag to true
        for branchName in branchNames:
            if branchName not in self.branchNames:
                # Generate a new branch name
                # for the branch
                folderName = "sphinxbuild_" + str(random.randint(0, 1000000000))

                # Clone a new repo there
                os.system(f"git clone {self.config.get('repo_url')} ../{folderName}")

                # Add to DB
                self.db.createBranch(branchName, folderName, mapping[branchName])

                # Elevate
                self.elevated = True
                self.elevatedTime = datetime.utcnow()

            elif mapping[branchName] != self.branchHashes[branchName]:
                # Rebuild the branch in a new thread
                thread = threading.Thread(
                    target=self._runBuildForBranch, args=(branchName,)
                )

                buildThreads.append(thread)
                thread.start()

                # Elevate
                self.elevated = True
                self.elevatedTime = datetime.utcnow()
        
        # Wait for all threads to finish
        for thread in buildThreads:
            thread.join()
        
        # Now, delete all branches that
        # have been deleted from git
        for branchName in branchNames:
            if branchName not in self.branchNames:
                # First, use site version to delete
                # all versions of the site
                for domain in self.domains:
                    version = SiteVersion(
                        branchName, domain, self.db.getBranchFolderName(branchName)
                    )

                    version.destroySite()
                
                # Now, delete the branch from the DB
                self.db.removeBranch(branchName)
        
    def runIter(self):
        """
        Wrapper function that calls the internal build logic,
        but also schedules the next iteration.
        """
        # Run the build logic
        self._runBuilds()

        # Schedule the next iteration
        if self.elevated:
            # First, check if we need to de-elevate
            if (datetime.utcnow() - self.elevatedTime).total_seconds() > 60:
                self.elevated = False
            else:
                # If we're elevated, run every 5 seconds
                schedule.every(5).seconds.do(self.runIter)
                return schedule.CancelJob
        
        # If we made it here, we're not elevated
        # and we should run every minute
        schedule.every(1).minutes.do(self.runIter)
        return schedule.CancelJob

if __name__ == "__main__":
    # Construct a runner and let
    # it run
    db = DB(DB_FNAME)
    config = Config("build.conf")
    runner = Runner(db, config)

    runner.runIter()

    while True:
        schedule.run_pending()
        time.sleep(1)


    # First, run a git fetch and pull

    # TODO: Use the production brach
    # as the base branch for the
    # autobuild
    # os.system("git fetch")

    # # Make a DB against the
    # # desired file name; pulls
    # # old data if applicable
    # db = DB(DB_FNAME)

    # # Make a config object
    # config = Config("build.conf")

    # # Get the repo url to pull from
    # repo_url = config.get("repo_url")

    # # Get the branch names from the git repo
    # repo = git.Repo("..")
    # branchNames = [branch.name for branch in repo.branches]

    # # First, create new branches that we need in the DB
    # for branchName in branchNames:
    #     if branchName not in db.getBranchNames():
    #         # Generate a new branch name
    #         # for the branch
    #         folderName = "sphinxbuild_" + str(random.randint(0, 1000000000))

    #         # Create the branch
    #         os.system(
    #             f"cd ..; mkdir -p {folderName}; cd {folderName}; git clone {repo_url} ."
    #         )

    #         # Add the branch to the DB
    #         db.createBranch(branchName, folderName)

    # # Now, delete branches that are in the DB, but not
    # # in the git repo
    # for branchName in db.getBranchNames():
    #     if branchName not in branchNames:
    #         # Delete the branch
    #         os.system(f"cd ..; rm -rf {db.getBranchFolderName(branchName)}")

    #         # Remove the branch from the DB
    #         db.removeBranch(branchName)

    # # At this point, we can start queing up
    # # autobuilds for each branch; once
    # # an autobuild is complete,
    # # it needs to schedule another
    # # build, which is timed base on whether
    # # or not it's a changing build. This
    # # can be handled nicely by invoking
    # # a member function on a deployment
    # # class
