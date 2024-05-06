#!/bin/bash

# This script will build the image a locally deploy a docker container for the enrich api

# build docker images
sudo docker build -t qr24:1.0 -f qr24.dockerfile .
