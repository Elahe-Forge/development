from aws_cdk import Duration, RemovalPolicy, Stack
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_notifications as s3n
from aws_cdk.aws_lambda_python_alpha import PythonFunction
from constructs import Construct


class CoiReaderStack(Stack):

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        env_name: str,
        env_account: str,
        env_region: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create an S3 bucket
        bucket = s3.Bucket(
            self,
            f"coi-reader-{env_name}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        ## PDF TEXTRACT LAMBDA FUNCTION
        # Create the Lambda function
        pdf_textract_lambda_fxn = PythonFunction(
            self,
            "PdfTextractFunction",
            entry="lambdas/pdfTextract",
            runtime=_lambda.Runtime.PYTHON_3_10,
            index="handler.py",
            handler="handler",
            architecture=_lambda.Architecture.ARM_64,
            memory_size=1024,
            timeout=Duration.seconds(300),
            environment={"BUCKET_NAME": bucket.bucket_name},
        )

        # Add a bucket policy to allow Textract to read objects from the bucket
        bucket.add_to_resource_policy(
            iam.PolicyStatement(
                actions=["s3:GetObject"],
                resources=[f"{bucket.bucket_arn}/*"],
                principals=[iam.ServicePrincipal("textract.amazonaws.com")],
            )
        )

        # Grant Lambda function permissions to access S3
        pdf_textract_lambda_fxn.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "s3:ListBucket",
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:GetBucketLocation",
                ],
                resources=[f"{bucket.bucket_arn}/*"],
            )
        )

        # Grant Lambda function permissions to read from the bucket
        bucket.grant_read(pdf_textract_lambda_fxn)

        # Grant Lambda function permissions to use Textract
        pdf_textract_lambda_fxn.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "textract:StartDocumentTextDetection",
                    "textract:GetDocumentTextDetection",
                ],
                resources=["*"],
            )
        )

        # Set up the S3 bucket notification to trigger the Lambda function
        pdf_textract_notification = s3n.LambdaDestination(pdf_textract_lambda_fxn)
        bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            pdf_textract_notification,
            s3.NotificationKeyFilter(prefix="inputs/pdfs/", suffix=".pdf"),
        )

        ## DATA EXTRACT LAMBDA FUNCTION
        # Create the Lambda function
        data_extract_lambda_fxn = PythonFunction(
            self,
            "DataExtractFunction",
            entry="lambdas/dataExtract",
            runtime=_lambda.Runtime.PYTHON_3_10,
            index="handler.py",
            handler="handler",
            architecture=_lambda.Architecture.ARM_64,
            memory_size=1024,
            timeout=Duration.seconds(600),
            environment={"BUCKET_NAME": bucket.bucket_name},
        )

        # Grant Lambda function permissions to access S3
        data_extract_lambda_fxn.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "s3:ListBucket",
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:GetBucketLocation",
                ],
                resources=[f"{bucket.bucket_arn}/*"],
            )
        )

        # Grant Lambda permission to access Secrets Manager
        data_extract_lambda_fxn.add_to_role_policy(
            iam.PolicyStatement(
                actions=["secretsmanager:GetSecretValue"],
                resources=[
                    f"arn:aws:secretsmanager:{env_region}:{env_account}:secret:data-science-and-ml-models/openai-Sc0RKh"
                ],
            )
        )

        # Grant Lambda function permissions to read from the bucket
        bucket.grant_read(data_extract_lambda_fxn)

        # Set up the S3 bucket notification to trigger the Lambda function
        data_extract_notification = s3n.LambdaDestination(data_extract_lambda_fxn)
        bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            data_extract_notification,
            s3.NotificationKeyFilter(prefix="outputs/document_txts/", suffix=".txt"),
        )

        ## DATA TRANSFORM EXCEL LAMBDA FUNCTION
        # Create the Lambda function
        data_transform_excel_lambda_fxn = PythonFunction(
            self,
            "DataTransformExcelFunction",
            entry="lambdas/dataTransformExcel",
            runtime=_lambda.Runtime.PYTHON_3_10,
            index="handler.py",
            handler="handler",
            architecture=_lambda.Architecture.ARM_64,
            memory_size=1024,
            timeout=Duration.seconds(600),
            environment={"BUCKET_NAME": bucket.bucket_name},
        )

        data_transform_excel_lambda_fxn.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "s3:ListBucket",
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:GetBucketLocation",
                ],
                resources=[f"{bucket.bucket_arn}/*"],
            )
        )

        # Grant Lambda permission to access Secrets Manager
        data_transform_excel_lambda_fxn.add_to_role_policy(
            iam.PolicyStatement(
                actions=["secretsmanager:GetSecretValue"],
                resources=[
                    f"arn:aws:secretsmanager:{env_region}:{env_account}:secret:data-science-and-ml-models/openai-Sc0RKh"
                ],
            )
        )

        # Grant Lambda function permissions to read from the bucket
        bucket.grant_read(data_transform_excel_lambda_fxn)

        # TRANSFORM NOTIFICATION
        # Set up the S3 bucket notification to trigger the Lambda function
        data_transform_notification = s3n.LambdaDestination(
            data_transform_excel_lambda_fxn
        )
        bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            data_transform_notification,
            s3.NotificationKeyFilter(prefix="outputs/config_json/", suffix=".json"),
        )

        # # Set up the S3 bucket notification to trigger the Lambda function
        # pdf_textract_notification = s3n.LambdaDestination(pdf_textract_lambda_fxn)
        # bucket.add_event_notification(
        #     s3.EventType.OBJECT_CREATED,
        #     pdf_textract_notification,
        #     s3.NotificationKeyFilter(prefix="inputs/pdfs/", suffix=".pdf"),
        # )
