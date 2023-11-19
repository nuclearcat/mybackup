#!/usr/bin/env python3

import json
import os
import sys
import requests
import argparse

metadata = {}

'''
Ask for admin password, then do call to /api/metadata and save it to metadata.json
'''
def retrieve_metadata():
    global metadata
    hostname = input("Enter hostname: ")
    password = input("Enter admin password: ")
    cname = input("Enter customer name: ")
    getdata = {'customername': cname}
    response = requests.get(f"https://${hostname}/api/metadata", auth=('admin', password), params=getdata)
    if response.status_code == 200:
        metadata = response.json()
        with open('metadata.json', 'w') as f:
            json.dump(metadata, f)
        print("Metadata saved to metadata.json")
    else:
        print("Failed to retrieve metadata. Details:")
        print("Status code:", response.status_code)
        print("Response body:", response.text)
        sys.exit(1)


'''
Load metadata json
'''
def load_config():
    global metadata
    # if not exist - retrieve metadata
    if not os.path.isfile('metadata.json'):
        retrieve_metadata()
    with open('metadata.json') as f:
        metadata = json.load(f)


def upload_backup(backup_file_path, url):
    global metadata
    # Check if the backup file is larger than 128MB
    if os.path.getsize(backup_file_path) > 128 * 1024 * 1024:
        print("Backup file is too large.")
        return
    # and 0 size not ok too
    if os.path.getsize(backup_file_path) == 0:
        print("Backup file is too small.")
        return

    # File size must be > 0 and < 128MB
    if not os.path.isfile(backup_file_path):
        print("Backup file does not exist.")
        return
    
    if os.path.getsize(backup_file_path) > 128 * 1024 * 1024 or os.path.getsize(backup_file_path) == 0:
        print("Backup file is too large or too small.")
        return

    # Prepare files for upload, load to buffer
    with open(backup_file_path, 'rb') as f:
        backup = f.read()
    files = {
        'backup': (os.path.basename(backup_file_path), backup, 'application/octet-stream')
    }

    # add metadata
    files['metadata'] = ('metadata', json.dumps(metadata), 'application/json')

    # Send POST request
    response = requests.post(url, files=files)

    return response


def verify_upload(r):
    if r.status_code == 200:
        try:
            j = r.json()
        except:
            print("Failed to parse response json.")
            print("Response body:", r.text)
            sys.exit(1)
        if j['status'] == 'OK':
            print("Backup uploaded successfully.")
        else:
            print("Failed to upload the backup. Details:")
            print("JSON Status:", j['status'])
            sys.exit(1)
    else:
        print("Failed to upload the backup. Details:")
        print("Status code:", r.status_code)
        print("Response body:", r.text)
        sys.exit(1)



if __name__ == "__main__":
    load_config()
    if len(sys.argv) != 2:
        print("Usage: python upload_client.py <backup_file or directory>")
        sys.exit(1)

    backup_file_path = sys.argv[1]
    url = f"https://{metadata['hostname']}/api/upload"

    # if it dir or file?
    if os.path.isdir(backup_file_path):
        # iterate over files in dir
        for filename in os.listdir(backup_file_path):
            # upload each file
            response = upload_backup(backup_file_path+'/'+filename, url)
            verify_upload(response)
    else:
        # upload single file
        response = upload_backup(backup_file_path, url)
        verify_upload(response)