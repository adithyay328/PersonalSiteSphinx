"""
This file defines the low-level
functionality for building and deploying
a version of the site from a version
of the site repo. The job of orchestrating
and running build jobs is left to a different
python file that invokes this script in
multiple processes.
"""
import os
import random
import sys

from jinja2 import Environment, FileSystemLoader

from data import DB, Config, DB_FNAME

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

      # Generate a random filename
      TEMP_FILENAME = str(random.randint(0, 10000)) + "temp.conf"
      if os.path.exists(TEMP_FILENAME):
         os.remove(TEMP_FILENAME)

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

      # Build the project
      assert(os.system(
         "cd ../docker && sudo ./SingleBuild.sh"
      ) == 0)

      # Now, delete the old build, if it
      # exists
      if os.path.exists(self.directoryName):
         os.system(f"sudo rm -rf {self.directoryName}")
      
      # Now, copy the build to the
      # correct directory, after making
      # sure that the directory exists
      os.system(f"sudo mkdir -p {self.directoryName}/html")
      assert(os.system(
         f"sudo cp -r ../site/build/* {self.directoryName}/html"
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
   
if __name__ == "__main__":
   # Get the branch name
   branchName = sys.argv[1]

   # Get list of domain name aliases
   # from config
   config = Config("build.conf")
   site_names = config.get("site_names")

   # Build each site version
   for domainName in site_names:
      # Create a SiteVersion object
      siteVersion = SiteVersion(branchName, domainName)

      # Build and deploy the site
      siteVersion.buildAndDeploy()