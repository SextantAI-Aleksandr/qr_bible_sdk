
""" This file is intended to 
1) Take a body of text as input
2) Find all the references to Bible passages in the text
3) Find all the Named Entities in the text
4) Return the text formatted with <a href> links, a list of bible refs, and a list of entities
"""

#~IMPORT~LIBRARIES~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
import requests
from os import environ
from functools import wraps
from flask import Flask, request, abort
from flask_cors import CORS, cross_origin
# Locally defined stuff
import enrich_text
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



#~~~Environment~Variables~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Get environment variable to aid in making calls to microservices
X_API_KEY = environ['X_API_KEY']
assert len(X_API_KEY) > 4 # ensure docker(compoe) didn't default to a blank string
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


#~~~~~~
#~~~Authorization~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def authorize(f):
    # reject a request if the api-key is not supplied
    # See https://stackoverflow.com/questions/34495632/how-to-implement-login-required-decorator-in-flask
    @wraps(f)
    def decorated_function(*args, **kws):
            api_key = request.headers.get("X-Api-Key", '')
            if not api_key == X_API_KEY:
                print('    UNAUTHORIZED REQUEST!')
                abort(401)
            return f(*args, **kws)            
    return decorated_function
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


#~Flask~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
app = Flask(__name__)
cors = CORS(app)


@app.route('/')
def echo():
    return {'message' : 'Hello from enrich_text'}


@app.route('/enrich', methods=['GET', 'POST'])
@authorize
def enrich_api():
    # give the document vectors for an array of documents
    req_id = request.json.get('req_id', None)
    text = request.json.get('text', '')
    print('    req_id={} text={}...'.format(req_id, text[:40]))
    resp, _ = enrich_text.enrich(text)
    resp['req_id'] = req_id
    return resp


if __name__ == '__main__': 
    #https://stackoverflow.com/questions/15878176/uwsgi-invalid-request-block-size
    app.run(host='0.0.0.0', port=5000)
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


