# Implements code to interact with the GitHub API
from github import Github
from github import Auth

import encrypt

GITHUB_KEY_FILE = "ghKey.enc.json"

class GHAPIHandle:
  def __init__(self, confFname : str, key : str, repoName : str, owner : str):
    """
    :param confFname: The filename of the encrypted GitHub API key
    :param key: The key to decrypt the GitHub API key with. Expected
      to be UTF-8 encoded.
    """
    # Loading the GitHub API key
    decrypted = encrypt.decryptFile(key, confFname)

    # Setting the GitHub API key
    self.githubAPIKey = decrypted["GITHUB_PERSONAL_ACCESS_TOKEN"]

    # Creating a github api object
    auth = Auth.Token(self.githubAPIKey)
    self.gh = Github(auth=auth)

    self.repoName = repoName
    self.owner = owner

  def getRemoteBranchesAndSHA(self):
    """
    :return: Returns a dictionary from
    branch name -> SHA hash.
    """

    # First, get the repo
    repo = self.gh.get_repo(self.owner + "/" + self.repoName)
    # Get all branches
    branches = repo.get_branches()

    result = {}

    # Iterate over and add to results
    for branch in branches:
      result[branch.name] = branch.commit.sha
    
    return result