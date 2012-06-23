#!usr/bin/python

import os
import sys
import fnmatch

# fileList = []
rootdir = sys.argv[1]
cnt = 0
folders = []
for root, subFolders, files in os.walk(rootdir):
    folders.append((root, cnt))
    for filename in files:
        if filename.lower().endswith(('.jpg', '.jpeg', '.gif', '.png')):
            cnt += 1
            #fileList.append(os.path.join(root, filename))
print cnt

