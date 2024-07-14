#!/bin/bash

VERSION="1.0.0"
BUILDS_FOLDER="builds"

if [ -d "${BUILDS_FOLDER}/node_search" ]; then
    rm -rf "${BUILDS_FOLDER}/node_search"
fi

mkdir -p "${BUILDS_FOLDER}/node_search"

# copy addon source files, remove pycache
cp -r *.py ${BUILDS_FOLDER}/node_search
cp -r blender_manifest.toml ${BUILDS_FOLDER}/node_search

# change version in bl_info to match one in this file
sed -i "s/\"version\": ([0-9], [0-9], [0-9])/\"version\": (`echo ${VERSION} | sed -e 's/\./, /g'`)/" ${BUILDS_FOLDER}/node_search/__init__.py


# remove old zip, zip everything
rm -f node_search*.zip
cd ${BUILDS_FOLDER}; zip -r ../node_search_${VERSION}.zip node_search/*
echo "Release zip saved at 'node_search_${VERSION}.zip'"