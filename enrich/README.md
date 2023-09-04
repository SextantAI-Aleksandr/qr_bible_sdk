# QR Bible Text Enrichment



One of the core features of QR Bible is the 'enrichment' API. Given a body of text, it will extract scripture references and named entities. 

## Deploying on AWS Lambda

The normal way to deploy this is to

* run ```build.sh``` to create the qrbible_enrich.zip zipfile
* upload this zipfile as a Lambda layer
* with that layer. upload the three python files (closest_bible_book.py, enrich_text.py, lambda_function.py) into a lambda function
* Set the function behind an API gateway



## Deploying locally



To deploy this API locally, set environment variables and run ```local-deploy.sh```. This will

* Build the *qrbible_enrich_loc_proto:1.0* image using ```local-enrich-proto.dockerfile``` 
* Build the dependent *qrbible_enrich_loc_api:1.0* image using ```local-enrich-api.dockerfile```
* Spins up a docker container running the ```local-run.py``` script

Note you may need to
sudo cp common_words.txt /opt/
sudo chown -R $USER:$USER /opt/common_words.txt


## to test the local deployment
curl -X GET \
    -d '{"text":"Lets go to Coffee Shop Bleau and study Exodus 22"}' \
    -H "Content-Type: application/json" \
    -H "X-Api-Key: $X_API_KEY"\
    http://127.0.0.1:22066/enrich
~                                     
