import json
import enrich_text



def lambda_handler(event, context):
    body = enrich_text.enrich(event['text'])
    return {
        'statusCode': 200,
        'body': json.dumps(body)
    }
