#!/bin/bash

# This will run a local container with the python code to do the enrichment
# It is intended to do one-time enrichment for populating verses


echo "VERIFY ENVIRONMENT VARIABLES: did you source from ~/.secrets/profiles/qrbible ?"
echo "ENRICH_PORT=$ENRICH_PORT"
echo "X_API_KEY=$X_API_KEY"
read -p "Press any key to continue..."
echo ""

# deploy a container
sudo docker run \
    -d \
    -p "127.0.0.1:${ENRICH_PORT}:5000" \
    -e "X_API_KEY=${X_API_KEY}" \
    --name qrbible_enrich_local qrbible_enrich_loc_api:1.1 

# to test the local container
curl -X GET \
    -d '{"text":"Lets go to Coffee Shop Bleau and study Exodus 22"}' \
    -H "Content-Type: application/json" \
    -H "X-Api-Key: $X_API_KEY"\
    http://127.0.0.1:22066/enrich
