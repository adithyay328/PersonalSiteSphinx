"""
This script is used to build the project
automatically as new branches are created,
and commits are pushed to the repository.

It is supposed to boot on startup, and
and it will work as follows:
1. Poll the repository for all branches,
   and note them in the JSON file used
   for tracking
2. For each branch, build the version
   of the project that is in that
   branch, and store the build in the
   correct build directory, also
   ensuring that the nginx
   configuration is pushed for that
   domain
3. Every minute, check if there are
   any new commits in any of the
   branches, and if there are, rebuild
   the site and mark it as changing.
4. If a branch is changing, we accelerate
   the modification checks to once
   every 5 seconds, and rebuild
   the site every time a commit is
   made.
5. If a branch marked as changing
   doesn't have a commit for 5
   minutes, we mark it as non-changing
   and go back to checking every
   minute.
"""
import os

from jinja2 import Environment, FileSystemLoader

class SiteVersion:
   def __init__(self, branchName : str, domainName : str):
      # Storing given values
      self.branchName = branchName
      self.domainName = domainName

      # Compute the remaining values
      self.completeDomainName = ( f"{branchName}." if branchName != "production" else "" ) + domainName
      self.directoryName = "/var/www/" + self.completeDomainName
      self.nginxConfigFileName = self.completeDomainName + ".conf"

   def _getNginxConfig(self) -> str:
      # Use jinja to generate the
      # nginx configuration file
      # for this site
      TEMPLATE_FILE = "nginxTemplate.conf"

      loader = FileSystemLoader(searchpath="./")

      # Here is the context we use
      # to generate the nginx
      # configuration text
      context = {
         "SITE_HTML_DIR" : self.directoryName,
         "COMPLETE_DOMAIN_NAME" : self.completeDomainName
      }

      # Now, render and return
      template = Environment(loader=loader).get_template(TEMPLATE_FILE)
      return template.render(context)

   def _writeNginxConfig(self) -> None:
      # First, if the config file is in
      # the sites-enabled directory, we
      # need to delete that link and
      # delete the nginx file in sites-available
      if self.nginxConfigFileName in os.listdir("/etc/nginx/sites-available"):
         os.system("sudo rm /etc/nginx/sites-enabled/" + self.nginxConfigFileName)
         os.system("sudo rm /etc/nginx/sites-available/" + self.nginxConfigFileName)

      NEW_NGINX_SITES_AVAILABLE_FILENAME = "/etc/nginx/sites-available/" + self.nginxConfigFileName
      NEW_NGINX_SITES_ENABLED_FILENAME = "/etc/nginx/sites-enabled/" + self.nginxConfigFileName
      
      # Now, write the nginx config file via a proxy
      # file, since open can't use root.
      TEMP_FILENAME = "temp.conf"
      with open(TEMP_FILENAME, "w") as nginxConfigFile:
         nginxConfigFile.write(self._getNginxConfig())
            
      # Now, copy the file to the correct
      # location
      assert(os.system(
         f"sudo cp {TEMP_FILENAME} {NEW_NGINX_SITES_AVAILABLE_FILENAME}"
      ) == 0)

      os.remove(TEMP_FILENAME)
      
      # Now, create a link to the
      # nginx config file in the
      # sites-enabled directory
      assert(os.system(
         f"sudo ln -s {NEW_NGINX_SITES_AVAILABLE_FILENAME} {NEW_NGINX_SITES_ENABLED_FILENAME}"
      ) == 0)

      # Done!

   def _buildAndCopy(self) -> None:
      """
      Builds the project and copies
      the build to the correct
      directory
      """

      # First, change to the correct branch
      # and pull the latest changes
      assert(os.system(
         f"git checkout {self.branchName} && git pull"
      ) == 0)

      # Now, build the project
      assert(os.system(
         "cd ../docker && sudo ./DockerRun.sh"
      ) == 0)

      # Now, delete the old build, if it
      # exists
      if os.path.exists(self.directoryName):
         os.system(f"sudo rm -rf {self.directoryName}")

      print(f"Copying build to {self.directoryName}")
      
      # Now, copy the build to the
      # correct directory, after making
      # sure that the directory exists
      os.system(f"sudo mkdir -p {self.directoryName}/html")
      assert(os.system(
         f"sudo cp -r ../site/build/html/* {self.directoryName}/html"
      ) == 0)

      # Done!
   
   def buildAndDeploy(self) -> None:
      """
      This function builds the project
      and deploys it to the correct
      directory
      """
      self._writeNginxConfig()
      self._buildAndCopy()

      # Reload nginx
      assert(os.system(
         "sudo systemctl restart nginx.service"
      ) == 0)

def buildAndDeploy(branchName : str, domainName : str) -> None:
   """
   This function takes in a
   branch name, and does the
   following things:
   1. Builds the project
      using the docker build
      script
   2. Copies the build to the
      correct directory
   3. Creates the correct
      nginx configuration
      for this site and
      copies it to the
      correct directory
   """
   # First, change to the right
   # correct directory and pull
   # the latest changes
   assert(os.system(
      f"git checkout {branchName} && git pull"
   ) == 0)

   # Now, build the project
   assert(os.system(
      "cd ../docker && ./DockerRun.sh"
   ) == 0)

   # Now, copy the build to the
   # correct directory; the
   # directory name convention
   # we use is:
   # /var/www/{subdomainname}.{domainname}
   # For example, if the branch name
   # is "test" and the domain name is
   # "example.com", then the directory
   # name will be:
   # /var/www/test.example.com, 
   # and the expected site name
   # is text.example.com.
   # There are some special branch names
   # like "production", which will be
   # deployed to the root domain.

   directoryName = "/var/www/" + ( f"{branchName}." if branchName != "production" else "" ) + domainName

   assert(os.system(
      f"cp -r ../site/build/html /var/www/{directoryName}"
   ) == 0)

   # Now, we need to create the
   # nginx configuration file
   # for this site

# Testing the nginx builder
if __name__ == "__main__":
   os.system("pip3 install Jinja2")

   # Build this site on the develop
   # branch
   siteVersion = SiteVersion("develop", "adithyay.com")
   siteVersion.buildAndDeploy()