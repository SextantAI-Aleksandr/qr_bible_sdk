#!/bin/bash 
# This builds the layer


set -e

TAG="qrbible_enrich:0.2"
ZIPFILE="qrbible_enrich.zip"

# Delete any previous version
rm -rf $ZIPFILE

sudo docker build -t $TAG .
CONTAINER=$(sudo docker run -d $TAG false)
echo "Copying layer.zip from the docker container"
sudo docker cp ${CONTAINER}:/layer.zip "${ZIPFILE}"
sudo chown -R "${USER}:${USER}" "${ZIPFILE}"
sudo docker container rm  ${CONTAINER}
echo "Created $ZIPFILE"
