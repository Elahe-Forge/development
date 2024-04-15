
"""
Scans the DynamoDB table for issuers and enqueue (SQS queue) issuer names if they meet the criteria (last visited more than 24 hours ago)
"""

import os
import boto3
import json
import logging
import time


logger = logging.getLogger()
logger.setLevel(logging.INFO)

def query_athena_and_wait_for_results(query, database, output_location):
    """
    Executes an SQL query on Athena and waits for the result.
    """
    athena_client = boto3.client('athena')

    execution_id = athena_client.start_query_execution(
        QueryString=query,
        QueryExecutionContext={'Database': database},
        ResultConfiguration={'OutputLocation': output_location}
    )['QueryExecutionId']
    

    while True:
        response = athena_client.get_query_execution(QueryExecutionId=execution_id)
        state = response['QueryExecution']['Status']['State']
        if state in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
            break
        time.sleep(1)

    if state != 'SUCCEEDED':
        status = response['QueryExecution']['Status']
        raise Exception(f"Athena query failed: State={state}, Status={status}")
    

    return athena_client.get_query_results(QueryExecutionId=execution_id)



def handler(event, context):

    athena_database = os.environ['ATHENA_DATABASE']
    athena_table = os.environ['ATHENA_TABLE']
    athena_output_location = os.environ['S3_OUTPUT_LOCATION']
    athena_query = f"SELECT COALESCE(legal_entity_name, issuer_id_name) AS name_or_id FROM {athena_table} limit 100"

    sqs_client = boto3.client('sqs')
    queue_url = os.environ['ISSUER_QUEUE_URL']

    # Determine the type of command (run-all or run-issuer)
    path = event.get('resource')  

    issuer_count = 0

    if path == '/run-all': 

        query_result = query_athena_and_wait_for_results(athena_query, athena_database, athena_output_location)
        
        for row in query_result['ResultSet']['Rows'][1:]:  # Skip the first row (header)
            issuer_name = row['Data'][0]['VarCharValue']
            logger.info(f"issuer_name: {issuer_name}")        
                
            try:
                payload = {'company_name': issuer_name}

                # Send message to SQS queue
                sqs_client.send_message(QueueUrl=queue_url, MessageBody=json.dumps(payload))
                issuer_count += 1
                logger.info(f"Enqueued message for {issuer_name} in SQS")

            except Exception as e:
                logger.error(f"Error enqueuing message for {issuer_name}: {str(e)}")

    elif path == '/run-issuer': 

        # Extract issuer from the body
        issuer_name = event.get('body', '').strip()
        if issuer_name:
            try:
                payload = {'company_name': issuer_name}
                sqs_client.send_message(QueueUrl=queue_url, MessageBody=json.dumps(payload))
                issuer_count = 1
                logger.info(f"Enqueued message for {issuer_name} in SQS")
            except Exception as e:
                logger.error(f"Error enqueuing message for {issuer_name}: {str(e)}")
        else:
            return {
                'statusCode': 400,
                'body': json.dumps('Issuer name is required for run-issuer command.')
            }

    else:
        return {
            'statusCode': 400,
            'body': json.dumps('Invalid command.')
        }
    
    # Return a success response
    return {
        'statusCode': 200,
        'body': json.dumps(f'Enqueued N={issuer_count} issuers.')
    }




