import json
import os

BUILD_CONFIG_FNAME = "buildConfig.json"
NGINX_SITE_SERVING_DIR = "/var/www/html"

def attemptGetField(fieldName : str, jsonDict : dict):
  """
  Attempts to get a field from a dictionary, and
  errors if it doesn't exist.
  """
  if fieldName not in jsonDict:
    raise RuntimeError(f"Required field {fieldName} not found in {BUILD_CONFIG_FNAME}!")

  return jsonDict[fieldName]

class BuildConfig:
  def __init__(self, fName : str):
    self.domainNames = []
    self.productionBranch = ""
    self.repoOwnerName = ""
    self.repoName = ""
    self.secondsBetweenBuilds = 0

    self.loadFromFName(fName)

  def loadFromFName(self, fName : str):
    """
    Loads the build config from a file.
    """
    if fName not in os.listdir():
      raise RuntimeError(f"No build config file found! Please create {fName}")

    with open(fName) as f:
      buildConfig = {}
      try:
        s = f.read()
        buildConfig.update(json.loads(s))
      except Exception as e:
        raise RuntimeError(f"Error parsing {fName} as JSON: {e}")

      # Try and access all the required fields, and
      # error if it doesn't work
      self.domainNames = attemptGetField("domain_names", buildConfig)
      self.productionBranch = attemptGetField("production_branch", buildConfig)
      self.repoOwnerName = attemptGetField("repo_owner_username", buildConfig)
      self.repoName = attemptGetField("repo_name", buildConfig)
      self.secondsBetweenBuilds = attemptGetField("seconds_between_builds", buildConfig)