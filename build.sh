#!/bin/bash

VERSION="0.0.1"
BUILDS_FOLDER="builds"

rm -rf ${BUILDS_FOLDER}/node_search

# copy addon source files, remove pycache
cp __init__.py ${BUILDS_FOLDER}/node_search

# change version in bl_info to match one in this file
sed -i "s/\"version\": ([0-9], [0-9], [0-9])/\"version\": (`echo ${VERSION} | sed -e 's/\./, /g'`)/" ${BUILDS_FOLDER}/node_search/__init__.py


# remove old zip, zip everything
rm -f node_search*.zip
cd ${BUILDS_FOLDER}; zip -r ../node_search_${VERSION}.zip node_search/*
echo "Release zip saved at 'node_search_${VERSION}.zip'"