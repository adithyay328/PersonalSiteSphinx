#!/usr/bin/env python3
import sys
import os

# Implements a sync script to allow easier development 
# across machines

if __name__ == "__main__":
  assert len(sys.argv) >= 2
  cmd = sys.argv[1]

  if cmd == "down":
    os.system("rsync -Prtz --delete ubuntu@44.232.105.119:/home/ubuntu/SoftwareDocuments/PersonalSiteSphinx ~/Documents/SoftwareProjects")
  elif cmd == "up":
    os.system("rsync -Prtz --delete ~/Documents/SoftwareProjects/PersonalSiteSphinx ubuntu@44.232.105.119:/home/ubuntu/SoftwareDocuments")
  else:
    raise ValueError("Invalid cmd")