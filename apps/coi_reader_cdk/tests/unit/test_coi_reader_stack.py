import aws_cdk as core
import aws_cdk.assertions as assertions

from coi_reader.coi_reader_stack import CoiReaderStack

# example tests. To run these tests, uncomment this file along with the example
# resource in coi_reader/coi_reader_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = CoiReaderStack(app, "coi-reader")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
