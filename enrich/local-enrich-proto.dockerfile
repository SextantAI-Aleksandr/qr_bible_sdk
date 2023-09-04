#!/bin/bash

# This builds a local 'base' image for running the enrich api
FROM python:3.8.5


RUN mkdir /opt/python
ADD common_words.txt /opt/


# Copy the necessary files
COPY local-run.pip .

# Install Python dependencies
RUN pip3 install -r local-run.pip

# Install Spacy
RUN python3 -m spacy download en_core_web_sm


