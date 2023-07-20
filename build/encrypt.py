# Contains some utilities for working with encrypted data
import json

import cryptography
from cryptography.fernet import Fernet

# This is a function that takes in a filename,
# and returns the decrypted dictionary
# that is stored in that file. Assumes
# that the file is a JSON file, but
# encrypted with Fernet.
def decryptFile(key, fName):
  key = key.encode("utf-8")
  with open(fName) as f:
    data = f.read()

    # Decrypt the data
    # and decode with utf-8
    decrypted = Fernet(key).decrypt(data.encode("utf-8")).decode("utf-8")

    # Load the JSON
    decryptedJSON = json.loads(decrypted)

    # Return the JSON
    return decryptedJSON

# This is a function that takes in a filename,
# and a dictionary, and writes the dictionary
# to the file, encrypted with Fernet.
def encryptFile(key, fName, data):
  key = key.encode("utf-8")
  with open(fName, "w") as f:
    # Dump the JSON
    dataJSON = json.dumps(data)

    # Encrypt the data
    encrypted = Fernet(key).encrypt(dataJSON.encode("utf-8")).decode("utf-8")

    # Write the encrypted data to the file
    f.write(encrypted)