
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
    aws_iam,
    aws_s3, 
    aws_s3_notifications,
    CfnOutput,
    aws_events,
    aws_events_targets
)
from constructs import Construct
import os


class NewsResearchStack(Stack):

    def __init__(self, scope: Construct, id: str, env_name: str, env_account: str, env_region: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Single DynamoDB table for all news entries
        news_table = aws_dynamodb.Table(
            self, 'data-science-news',
            table_name=f'data-science-news-{env_name}',
            partition_key=aws_dynamodb.Attribute(name='company_name_link_date', type=aws_dynamodb.AttributeType.STRING),
            sort_key=aws_dynamodb.Attribute(name='date', type=aws_dynamodb.AttributeType.STRING),
            stream= aws_dynamodb.StreamViewType.NEW_AND_OLD_IMAGES
        ) 

        # DLQ for issuer queue
        issuer_dlq = aws_sqs.Queue(
            self, "NewsIssuerDLQ",
            queue_name=f"NewsIssuerDLQ-{env_name}",
            visibility_timeout=Duration.seconds(300),
            retention_period=Duration.days(14)  # Messages are retained for 14 days
        )


        # SQS Queue for communication between news_endpoint and news_fetcher 
        issuer_queue = aws_sqs.Queue(
            self, 'NewsIssuerQueue',
            visibility_timeout=Duration.seconds(960), # 16 mins - slightly higher than lambda timeout
            queue_name=f"NewsIssuerQueue-{env_name}",
            dead_letter_queue=aws_sqs.DeadLetterQueue(
                max_receive_count=5,  # Number of receive attempts before moving to DLQ
                queue=issuer_dlq
            )
        )

        # DLQ for the queue between news_fetcher and news_consumer
        llm_consumer_dlq = aws_sqs.Queue(
            self, "NewsLlmConsumerDLQ",
            queue_name=f"NewsLlmConsumerDLQ-{env_name}",
            visibility_timeout=Duration.seconds(300),
            retention_period=Duration.days(14)
        )

        # SQS Queue for communication between news_fetcher and news_consumer
        llm_consumer_queue = aws_sqs.Queue(
            self, "NewsLlmConsumerQueue",
            queue_name=f"NewsLlmConsumerQueue-{env_name}",
            visibility_timeout=Duration.seconds(960), # 16 mins - slightly higher than lambda timeout
            dead_letter_queue=aws_sqs.DeadLetterQueue(
                max_receive_count=5,
                queue=llm_consumer_dlq
            )
        )

        dlq_handler_ecr_image = aws_lambda.EcrImageCode.from_asset_image(
                directory = os.path.join(os.getcwd(), "lambda/dlq_handler"),
                platform = aws_ecr_assets.Platform.LINUX_AMD64
        )

        # Lambda function to process messages from DLQs
        dlq_handler_lambda = aws_lambda.Function(self,
            id            = "NewsDLQHandlerLambdaFunction",
            description   = "NewsDLQHandlerLambdaFunction",
            code          = dlq_handler_ecr_image,
            handler       = aws_lambda.Handler.FROM_IMAGE,
            runtime       = aws_lambda.Runtime.FROM_IMAGE,
            environment={
                'ISSUER_DLQ_URL': issuer_dlq.queue_url,
                'LLM_CONSUMER_DLQ_URL': llm_consumer_dlq.queue_url
            },
            function_name = f"NewsDLQHandlerFunction-{env_name}",
            memory_size   = 128,
            reserved_concurrent_executions = 10,
            timeout       = Duration.seconds(60),
        )

        # Attach the DLQs as event sources to the Lambda function
        dlq_handler_lambda.add_event_source(lambda_event_source.SqsEventSource(issuer_dlq, batch_size=1))
        dlq_handler_lambda.add_event_source(lambda_event_source.SqsEventSource(llm_consumer_dlq, batch_size=1))

        # Grant the Lambda function permissions to process messages from both DLQs
        issuer_dlq.grant_consume_messages(dlq_handler_lambda)
        llm_consumer_dlq.grant_consume_messages(dlq_handler_lambda)


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
                'ISSUER_QUEUE_URL': issuer_queue.queue_url,
                'LLM_CONSUMER_QUEUE_URL': llm_consumer_queue.queue_url
          },
          function_name = f"NewsFetcherFunction-{env_name}",
          memory_size   = 128,
          reserved_concurrent_executions = 10,
          timeout       = Duration.seconds(60),
        )

        # Grant the Lambda function permissions to read and write to the table
        news_table.grant_write_data(news_fetcher_lambda)
        news_table.grant_read_data(news_fetcher_lambda)
        
        # Grant the Lambda function permissions to read from the queue
        issuer_queue.grant_consume_messages(news_fetcher_lambda)
        
        #Create an SQS event source for Lambda
        issuers_event_source = lambda_event_source.SqsEventSource(issuer_queue)

        #Add SQS event source to the Lambda function
        news_fetcher_lambda.add_event_source(issuers_event_source)

        # Allow the news_fetcher Lambda to send messages to the consumer queue
        llm_consumer_queue.grant_send_messages(news_fetcher_lambda)

        # Grant read access to the secret manager for lambda
        serpapi_api_key = f"arn:aws:secretsmanager:{env_region}:{env_account}:secret:data-science-and-ml-models/serpapi_token-utuxE8" if env_name == 'dev' else f"arn:aws:secretsmanager:{env_region}:{env_account}:secret:data-science-and-ml-models/serpapi_token-2pniBL"

        secret_manager = aws_secretsmanager.Secret.from_secret_complete_arn(self, 'data-science-and-ml-models/serpapi_token', serpapi_api_key)
        secret_manager.grant_read(news_fetcher_lambda)

        news_endpoints_ecr_image = aws_lambda.EcrImageCode.from_asset_image(
                directory = os.path.join(os.getcwd(), "lambda/serp_api_producer/news_endpoints"),
                platform = aws_ecr_assets.Platform.LINUX_AMD64,
        )
        
        news_input_location = "data-science-news-issuer-list" if env_name == 'dev' else "data-science-news-issuer-list-prod"
        athena_database = "datalake-curated-dev" if env_name == 'dev' else "datalake-curated-production"
        athena_table = "icms_issuer" 
        s3_athena_output_location = "s3://newsresearch/" if env_name == 'dev' else "s3://news-research/"

        news_endpoints_lambda = aws_lambda.Function(self,
          id            = "NewsEndpointsLambdaFunction",
          description   = "NewsEndpointsLambdaFunction",
          code          = news_endpoints_ecr_image,
          handler       = aws_lambda.Handler.FROM_IMAGE,
          runtime       = aws_lambda.Runtime.FROM_IMAGE,
          environment  ={
                'ISSUER_QUEUE_URL': issuer_queue.queue_url,
                'ATHENA_DATABASE': athena_database,
                'ATHENA_TABLE': athena_table, 
                'S3_EXCEL_SHEET_LOCATION': news_input_location,
                'S3_OUTPUT_LOCATION': s3_athena_output_location,
                'DEFAULT_NUMBER_OF_ARTICLES': '5',
                'DEFAULT_GET_SUMMARY': 'true'
          },
          function_name = f"NewsEndpointsFunction-{env_name}",
          memory_size   = 1024, 
          reserved_concurrent_executions = 10,
          timeout       = Duration.seconds(900),
        )
        
        s3_policy = aws_iam.PolicyStatement(
            effect=aws_iam.Effect.ALLOW,
            actions=["s3:GetBucketLocation","s3:ListBucketMultipartUploads", "s3:GetObject", "s3:PutObject", "s3:ListBucket"],
            resources=["arn:aws:s3:::*"]
        )
        news_endpoints_lambda.add_to_role_policy(s3_policy)
               
        athena_policy = aws_iam.PolicyStatement(
            effect=aws_iam.Effect.ALLOW,
            actions=["athena:StartQueryExecution", "athena:GetQueryExecution", "athena:GetQueryResults"],
            resources=["arn:aws:athena:*:*:*"]  
        )
        news_endpoints_lambda.add_to_role_policy(athena_policy)

        glue_policy = aws_iam.PolicyStatement(
            effect=aws_iam.Effect.ALLOW,
            actions=["glue:GetDatabase","glue:GetDatabases","glue:GetTable","glue:GetTables"],
            resources=["arn:aws:glue:*:*:catalog","arn:aws:glue:*:*:database/*","arn:aws:glue:*:*:table/*/*"]
        )
        news_endpoints_lambda.role.add_to_policy(glue_policy)


        # Grant the Parent Lambda permission to send messages to the queue
        issuer_queue.grant_send_messages(news_endpoints_lambda)


        # API Gateway to trigger the Lambda function 
        api = aws_apigateway.LambdaRestApi(
            self, 'NewsApi',
            handler=news_endpoints_lambda,
            proxy=False,
            rest_api_name=f'NewsApi-{env_name}'
        )

        # Resource for running all companies
        run_all_resource = api.root.add_resource('run-all')
        run_all_resource.add_method('POST', request_parameters={
                'method.request.querystring.number_of_articles': False,  # Optional to provide
                'method.request.querystring.get_summary': False          # Optional to provide 
            }
        )

        # Resource for running a specific issuer
        run_issuer_resource = api.root.add_resource('run-issuer')
        run_issuer_resource.add_method('POST', request_parameters={
                'method.request.querystring.number_of_articles': False,  
                'method.request.querystring.get_summary': False           
            }
        )

        # Resource for running an excel sheet from s3
        run_s3_resource = api.root.add_resource('run-s3')
        run_s3_resource.add_method('POST', request_parameters={
                'method.request.querystring.number_of_articles': False,  
                'method.request.querystring.get_summary': False           
            }
        )


        S3_icms_bucket = "fg-acceptance-issuersapp-extracts" if env_name =='dev' else "fg-prod-issuersapp-extracts"
        
        icms_bucket = aws_s3.Bucket.from_bucket_name(
            self, f"IssuersAppExtracts-{env_name}",
            bucket_name=S3_icms_bucket
        )

        # Grant the Lambda function permissions to read from the S3 icms bucket
        icms_bucket.grant_read(news_endpoints_lambda)

        # Add notification for S3 icms bucket to trigger the Lambda function
        notification = aws_s3_notifications.LambdaDestination(news_endpoints_lambda)
        icms_bucket.add_event_notification(
            aws_s3.EventType.OBJECT_CREATED,
            notification,
            aws_s3.NotificationKeyFilter(prefix="projections/issuerProjection/")
        )


        # Define the IAM role for news_consumer Lambda
        lambda_role = aws_iam.Role(self, "NewsLambdaExecutionRole",
                                   assumed_by=aws_iam.ServicePrincipal("lambda.amazonaws.com"),
                                   managed_policies=[
                                       aws_iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
                                       aws_iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaVPCAccessExecutionRole")
                                   ])

        # Custom policy to allow invoking Bedrock model
        lambda_role.add_to_policy(aws_iam.PolicyStatement(
            effect=aws_iam.Effect.ALLOW,
            actions=["bedrock:InvokeModel"],
            resources=["arn:aws:bedrock:us-west-2::foundation-model/*"]
        ))

        # Policy to allow this Lambda to invoke another Lambda function
        lambda_role.add_to_policy(aws_iam.PolicyStatement(
            effect=aws_iam.Effect.ALLOW,
            actions=["lambda:InvokeFunction"],
            resources=["arn:aws:lambda:us-west-2:*:function:*"]  
        ))

        news_consumer_ecr_image = aws_lambda.EcrImageCode.from_asset_image(
            # directory = os.path.join(os.getcwd(), "lambda/llm_consumer/news_consumer"),
            directory=os.path.join(os.getcwd(), ""),  # Adjust the path to include the project root
            file="lambda/llm_consumer/news_consumer/Dockerfile",
            platform = aws_ecr_assets.Platform.LINUX_AMD64
        )

        news_output_location = "data-science-news-output" if env_name == 'dev' else "data-science-news-output-prod"
        news_prompts_location = "data-science-news-prompts" if env_name == 'dev' else "data-science-news-prompts-prod"

        news_consumer_lambda = aws_lambda.Function(self,
          id            = "NewsConsumerLambdaFunction",
          description   = "NewsConsumerLambdaFunction",
          code          = news_consumer_ecr_image,
          handler       = aws_lambda.Handler.FROM_IMAGE,
          runtime       = aws_lambda.Runtime.FROM_IMAGE,
          role=lambda_role,
          environment   = {
                'S3_NEWS_OUTPUT_BUCKET': news_output_location,
                'MODEL_NAME': 'anthropic.claude', #'gpt'
                'MODEL_VERSION': 'v2', #'3.5-turbo'
                'S3_NEWS_PROMPTS_BUCKET': news_prompts_location,
                'PROMPT_VERSION': 'v1'
          },
          function_name = f"NewsConsumerFunction-{env_name}",
          memory_size   = 1024, # default 128 causes memory allocation limit error
          reserved_concurrent_executions = 10,
          timeout       = Duration.seconds(900),
        )

        # Attach the llm consumer queue as an event source to the news_consumer Lambda
        news_consumer_event_source = lambda_event_source.SqsEventSource(llm_consumer_queue)
        news_consumer_lambda.add_event_source(news_consumer_event_source)

        news_consumer_lambda.add_to_role_policy(s3_policy)

        openai_api_key = f"arn:aws:secretsmanager:{env_region}:{env_account}:secret:data-science-and-ml-models/openai-Sc0RKh" if env_name == 'dev' else f"arn:aws:secretsmanager:{env_region}:{env_account}:secret:data-science-and-ml-models/openai-8d8fB2"

        secret_manager = aws_secretsmanager.Secret.from_secret_complete_arn(self, 'data-science-and-ml-models/openai', openai_api_key)
        secret_manager.grant_read(news_consumer_lambda)

        # Output the API Gateway URL
        output_api_url = CfnOutput(
            self, "NewsApiURL",
            value=api.url,
            description="The URL of the News API Gateway"
        )

        # If prod, schedule weekly run + weekly email
        if env_name == 'prod': 

            # IAM Role for EventBridge to Invoke API Gateway
            eventbridge_role = aws_iam.Role(
                self, "NewsEventBridgeApiGatewayRole",
                assumed_by=aws_iam.ServicePrincipal("events.amazonaws.com"),
                inline_policies={
                    "InvokeApiPolicy": aws_iam.PolicyDocument(
                        statements=[
                            aws_iam.PolicyStatement(
                                actions=["execute-api:Invoke"],
                                resources=[api.arn_for_execute_api("*/*/*")],  
                                effect=aws_iam.Effect.ALLOW
                            )
                        ]
                    )
                }
            )

            # EventBridge Rule to trigger the API Gateway
            eventbridge_rule = aws_events.Rule(
                self, "NewsApiTriggerRule",
                schedule=aws_events.Schedule.cron(minute="0", hour="17", month="*", week_day="MON")  
                # schedule=aws_events.Schedule.expression("rate(2 minutes)") 
            )
            
            eventbridge_rule.add_target(aws_events_targets.ApiGateway(
                rest_api=api,
                stage="prod",
                method="POST",
                path="/run-s3",  
                header_parameters={"Content-Type": "application/json"},
                post_body=aws_events.RuleTargetInput.from_text("05-21-24/"),
                event_role=eventbridge_role,
                # retry_attempts=0,
                # dead_letter_queue=dlq
            ))

            # Lambda to send emails with latest news
            email_producer_ecr_image = aws_lambda.EcrImageCode.from_asset_image(
                    directory = os.path.join(os.getcwd(), "lambda/email_producer"),
                    platform = aws_ecr_assets.Platform.LINUX_AMD64,
            )
            
            email_producer_lambda = aws_lambda.Function(self,
            id            = "NewsEmailProducerLambdaFunction",
            description   = "NewsEmailProducerLambdaFunction",
            code          = email_producer_ecr_image,
            handler       = aws_lambda.Handler.FROM_IMAGE,
            runtime       = aws_lambda.Runtime.FROM_IMAGE,
            environment  ={
                    'S3_NEWS_OUTPUT_LOCATION': news_output_location,
            },
            function_name = f"NewsEmailProducerFunction-{env_name}",
            memory_size   = 1024, 
            reserved_concurrent_executions = 10,
            timeout       = Duration.seconds(900),
            )

            news_output_bucket = aws_s3.Bucket.from_bucket_name(
                self, f"S3NewsOutputLocation-{env_name}",
                bucket_name=news_output_location
            )

            # Grant the Lambda function permissions to read from the S3 bucket
            news_output_bucket.grant_read(email_producer_lambda)

            # SES permissions
            email_producer_lambda.add_to_role_policy(
                aws_iam.PolicyStatement(
                    actions=["ses:SendRawEmail"],
                    resources=["*"]
                )
            )

            # EventBridge rule for sending email
            email_rule = aws_events.Rule(
                self, "NewsEmailRule",
                # schedule=aws_events.Schedule.cron(minute="0", hour="17", month="*", week_day="TUE") 
                schedule=aws_events.Schedule.expression("rate(2 minutes)") 
            )
            email_rule.add_target(aws_events_targets.LambdaFunction(email_producer_lambda))


