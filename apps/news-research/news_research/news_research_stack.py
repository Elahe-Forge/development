
from aws_cdk import (
    aws_lambda,
    aws_dynamodb,
    Stack,
    Duration,
    aws_apigateway,
    aws_secretsmanager,
    aws_sqs,
    aws_lambda_event_sources as lambda_event_source
)
from constructs import Construct



class NewsResearchStack(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # DynamoDB table for issuers
        issuers_table = aws_dynamodb.Table.from_table_name(
            self, 'news-research-issuers-table',
            table_name='news-research-issuers-table'
        )

        # Single DynamoDB table for all news entries
        news_table = aws_dynamodb.Table(
            self, 'news-table',
            table_name='news-table',
            sort_key=aws_dynamodb.Attribute(name='position', type=aws_dynamodb.AttributeType.NUMBER),
            partition_key=aws_dynamodb.Attribute(name='company_name', type=aws_dynamodb.AttributeType.STRING)
        )

        # SQS Queue for issuers
        issuer_queue = aws_sqs.Queue(
            self, 'IssuerQueue',
            visibility_timeout=Duration.seconds(600) #-> 30 sec is the default
        )

        # Child Lambda function for fetching and updating news
        news_fetcher_child_lambda = aws_lambda.Function(
            self, "NewsFetcherChildLambdaFunction",
            runtime=aws_lambda.Runtime.PYTHON_3_9,
            handler="child_lambda_function.handler",  
            code=aws_lambda.Code.from_asset("./build.zip"),
            environment={
                'NEWS_TABLE': news_table.table_name,
                'ISSUERS_TABLE_NAME': issuers_table.table_name,
                'ISSUER_QUEUE_URL': issuer_queue.queue_url
            },
            timeout=Duration.seconds(60)
        )

        # Grant the Lambda function permissions to write to the table
        news_table.grant_write_data(news_fetcher_child_lambda)
        issuers_table.grant_read_write_data(news_fetcher_child_lambda)
        
        # Grant the Child Lambda function permissions to read from the queue
        issuer_queue.grant_consume_messages(news_fetcher_child_lambda)
        
        #Create an SQS event source for Lambda
        issuers_event_source = lambda_event_source.SqsEventSource(issuer_queue)

        #Add SQS event source to the Lambda function
        news_fetcher_child_lambda.add_event_source(issuers_event_source)

        # Grant read access to the secret manager for lambda
        secret_manager = aws_secretsmanager.Secret.from_secret_complete_arn(self, 'news-research-data-science', 'arn:aws:secretsmanager:us-west-2:597915789054:secret:news-research-data-science-4jO5Zo' )
        secret_manager.grant_read(news_fetcher_child_lambda)


        # Parent Lambda function
        news_fetcher_lambda = aws_lambda.Function(
            self, "NewsFetcherLambdaFunction",
            runtime=aws_lambda.Runtime.PYTHON_3_9,
            handler="lambda_function.handler",
            code=aws_lambda.Code.from_asset("./lambda/serp_api_producer"),
            environment={
                'ISSUERS_TABLE_NAME': issuers_table.table_name,
                'ISSUER_QUEUE_URL': issuer_queue.queue_url
            },
            # timeout=Duration.seconds(60)
        )

        # Grant the parent Lambda permission to read the table
        issuers_table.grant_read_data(news_fetcher_lambda)

        # Grant the Parent Lambda permission to send messages to the queue
        issuer_queue.grant_send_messages(news_fetcher_lambda)


        # API Gateway to trigger the Lambda function
        api = aws_apigateway.LambdaRestApi(
            self, 'NewsApi',
            handler=news_fetcher_lambda,
            proxy=False
        )

        # Resource for running all companies
        run_all_resource = api.root.add_resource('run-all')
        run_all_resource.add_method('POST')

        # Resource for running a specific issuer
        run_issuer_resource = api.root.add_resource('run-issuer')
        run_issuer_resource.add_method('POST')

    














