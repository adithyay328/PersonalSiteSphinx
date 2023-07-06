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
    
    def setAllBranchesNotChanging(self):
        self._db.update({"changing" : False}, Query().changing == True)
    
    def setBranchChanging(self, branchName : str):
        self._db.update({"changing" : True}, Query().branchName == branchName)
    
    def setBranchNotChanging(self, branchName : str):
        self._db.update({"changing" : False}, Query().branchName == branchName)
    
    def createBranch(self, branchName : str, folderName : str):
        self._db.insert({
            "branchName" : branchName,
            "folderName" : folderName,
            "changing" : False,
            "time_utc_string" : datetime.utcnow().isoformat()
        })
    
    def updateTime(self, branchName : str):
        self._db.update({"time_utc_string" : datetime.utcnow().isoformat()}, Query().branchName == branchName)
    
    def getBranchFolderName(self, branchName : str):
        return self._db.get(Query().branchName == branchName)["folderName"]

    def getBranchChanging(self, branchName : str):
        return self._db.get(Query().branchName == branchName)["changing"]

    def getBranchUpdateTime(self, branchName : str):
        return datetime.fromisoformat(self._db.get(Query().branchName == branchName)["time_utc_string"])
    
    def getBranchNames(self):
        return [branch["branchName"] for branch in self._db.all()]

    def removeBranch(self, branchName : str):
        self._db.remove(Query().branchName == branchName)