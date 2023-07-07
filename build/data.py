import json
from datetime import datetime

from tinydb import TinyDB, Query

DB_FNAME = "db.json"

class Config:
    """
    A class that makes it easy
    to access all config info
    """
    def __init__(self, fName : str = "build.conf"):
        self.data = {}
        with open(fName) as f:
            self.data = json.load(f)
    
    def get(self, key : str):
        return self.data[key]

class DB:
    def __init__(self, db_Fname : str = DB_FNAME):
        self._db = TinyDB(db_Fname)
    
    def createBranch(self, branchName : str, folderName : str, sha_hash : str):
        self._db.insert({
            "branchName" : branchName,
            "folderName" : folderName,
            "sha_hash" : sha_hash,
        })
    
    def updateHash(self, branchName : str, sha_hash : str):
        self._db.update({"sha_hash" : sha_hash}, Query().branchName == branchName)
    
    def getBranchFolderName(self, branchName : str):
        return self._db.get(Query().branchName == branchName)["folderName"]

    def getBranchHash(self, branchName : str):
        return self._db.get(Query().branchName == branchName)["sha_hash"]
    
    def getBranchNames(self):
        return [branch["branchName"] for branch in self._db.all()]

    def removeBranch(self, branchName : str):
        self._db.remove(Query().branchName == branchName)