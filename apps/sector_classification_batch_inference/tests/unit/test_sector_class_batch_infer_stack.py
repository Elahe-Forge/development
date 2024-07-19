import aws_cdk as core
import aws_cdk.assertions as assertions

from cdk_batch_infer.cdk_batch_infer_stack import SectorClassBatchInferStack


# example tests. To run these tests, uncomment this file along with the example
# resource in cdk_batch_infer/cdk_batch_infer_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = SectorClassBatchInferStack(app, "sector-class-batch-infer")
    template = assertions.Template.from_stack(stack)


#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
