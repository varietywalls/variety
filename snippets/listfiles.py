#!usr/bin/python

import os
import sys
import fnmatch

fileList = []
rootdir = sys.argv[1]
for root, subFolders, files in os.walk(rootdir):
    for filename in fnmatch.filter(files, '*.jpg'):
        fileList.append(os.path.join(root, filename))
print fileList

