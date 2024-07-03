import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk_model_train_sector.cdk_model_train_sector_stack import CdkModelTrainSectorStack

# example tests. To run these tests, uncomment this file along with the example
# resource in cdk_model_train_sector/cdk_model_train_sector_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = CdkModelTrainSectorStack(app, "cdk-model-train-sector")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
