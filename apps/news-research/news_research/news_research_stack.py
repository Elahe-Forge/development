
from aws_cdk import (
    aws_lambda,
    aws_dynamodb,
    Stack,
    Duration,
    aws_apigateway,
    aws_secretsmanager,
    aws_sqs,
    aws_lambda_event_sources as lambda_event_source,
    aws_ecr_assets,
)
from constructs import Construct
import os



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
            partition_key=aws_dynamodb.Attribute(name='company_name', type=aws_dynamodb.AttributeType.STRING),
            stream= aws_dynamodb.StreamViewType.NEW_AND_OLD_IMAGES
        )

        # SQS Queue for issuers
        issuer_queue = aws_sqs.Queue(
            self, 'IssuerQueue',
            visibility_timeout=Duration.seconds(600) #-> 30 sec is the default
        )

        news_fetcher_ecr_image = aws_lambda.EcrImageCode.from_asset_image(
                directory = os.path.join(os.getcwd(), "lambda/serp_api_producer/news_fetcher"),
                platform = aws_ecr_assets.Platform.LINUX_AMD64
        )

        news_fetcher_lambda = aws_lambda.Function(self,
          id            = "NewsFetcherLambdaFunction",
          description   = "NewsFetcherLambdaFunction",
          code          = news_fetcher_ecr_image,
          handler       = aws_lambda.Handler.FROM_IMAGE,
          runtime       = aws_lambda.Runtime.FROM_IMAGE,
          environment   = {
                'NEWS_TABLE': news_table.table_name,
                'ISSUERS_TABLE_NAME': issuers_table.table_name,
                'ISSUER_QUEUE_URL': issuer_queue.queue_url
          },
          function_name = "NewsFetcherFunction",
          memory_size   = 128,
          reserved_concurrent_executions = 10,
          timeout       = Duration.seconds(60),
        )

        # Grant the Lambda function permissions to write to the table
        news_table.grant_write_data(news_fetcher_lambda)
        issuers_table.grant_read_write_data(news_fetcher_lambda)
        
        # Grant the Child Lambda function permissions to read from the queue
        issuer_queue.grant_consume_messages(news_fetcher_lambda)
        
        #Create an SQS event source for Lambda
        issuers_event_source = lambda_event_source.SqsEventSource(issuer_queue)

        #Add SQS event source to the Lambda function
        news_fetcher_lambda.add_event_source(issuers_event_source)

        # Grant read access to the secret manager for lambda
        secret_manager = aws_secretsmanager.Secret.from_secret_complete_arn(self, 'news-research-data-science', 'arn:aws:secretsmanager:us-west-2:597915789054:secret:news-research-data-science-4jO5Zo' )
        secret_manager.grant_read(news_fetcher_lambda)


        news_endpoints_ecr_image = aws_lambda.EcrImageCode.from_asset_image(
                directory = os.path.join(os.getcwd(), "lambda/serp_api_producer/news_endpoints"),
                platform = aws_ecr_assets.Platform.LINUX_AMD64,
        )

        news_endpoints_lambda = aws_lambda.Function(self,
          id            = "NewsEndpointsLambdaFunction",
          code          = news_endpoints_ecr_image,
          handler       = aws_lambda.Handler.FROM_IMAGE,
          runtime       = aws_lambda.Runtime.FROM_IMAGE,
          environment  ={
                'ISSUERS_TABLE_NAME': issuers_table.table_name,
                'ISSUER_QUEUE_URL': issuer_queue.queue_url
          },
          function_name = "NewsEndpointsFunctionx",
          memory_size   = 128,
          reserved_concurrent_executions = 10,
          timeout       = Duration.seconds(60),
        )

        # Grant the parent Lambda permission to read the table
        issuers_table.grant_read_data(news_endpoints_lambda)

        # Grant the Parent Lambda permission to send messages to the queue
        issuer_queue.grant_send_messages(news_endpoints_lambda)


        # API Gateway to trigger the Lambda function
        api = aws_apigateway.LambdaRestApi(
            self, 'NewsApi',
            handler=news_endpoints_lambda,
            proxy=False
        )

        # Resource for running all companies
        run_all_resource = api.root.add_resource('run-all')
        run_all_resource.add_method('POST')

        # Resource for running a specific issuer
        run_issuer_resource = api.root.add_resource('run-issuer')
        run_issuer_resource.add_method('POST')



        news_consumer_ecr_image = aws_lambda.EcrImageCode.from_asset_image(
            directory = os.path.join(os.getcwd(), "lambda/llm_consumer/news_consumer"),
            platform = aws_ecr_assets.Platform.LINUX_AMD64
        )

        news_consumer_lambda = aws_lambda.Function(self,
          id            = "NewsConsumerLambdaFunction",
          description   = "NewsConsumerLambdaFunction",
          code          = news_consumer_ecr_image,
          handler       = aws_lambda.Handler.FROM_IMAGE,
          runtime       = aws_lambda.Runtime.FROM_IMAGE,
          environment   = {
                'NEWS_TABLE': news_table.table_name,
          },
          function_name = "NewsConsumerFunction",
          memory_size   = 128,
          reserved_concurrent_executions = 10,
          timeout       = Duration.seconds(60),
        )

        news_table.grant_read_data(news_consumer_lambda)
        news_table_event_source =  lambda_event_source.DynamoEventSource(news_table, starting_position= aws_lambda.StartingPosition.LATEST)
        news_consumer_lambda.add_event_source(news_table_event_source)


    














