
# News Research Project
This AWS-based project operates on a serverless architecture, primarily using Lambda functions, DynamoDB, and SQS, orchestrated through AWS CDK. The central mechanism involves two Lambda functions: a parent function that scans the DynamoDB `news-research-issuers-table` for companies (issuers) requiring news updates, and a child function that fetches news for each issuer using SerpAPI. When the parent function identifies issuers needing updates (if `last_visited` attribute is updated more than 24 hours ago), it enqueues these tasks into an SQS queue. 
The child function, triggered by messages in this queue, processes each issuer independently, retrieving relevant news and storing it in `news-table` DynamoDB table. This design allows for the child function instances running in parallel to handle multiple issuers simultaneously. The entire setup is defined and deployed using AWS CDK.

## Steps to Run

1. Install Python version 3.9 or later

2. Install Node.js and npm
    - AWS CDK is developed in Node.js, so you need to install Node.js and npm.

3. Install AWS Command Line Interface (CLI)
    - Once installed, configure it by running `aws configure` in your terminal.
    - Enter your AWS Access Key ID, Secret Access Key, default region name, and default output format. These credentials are available in your AWS Management Console under IAM (Identity and Access Management).
    - Add `AdministratorAccess` in your user's permission policy.

4. Clone the Repository

5. Create a virtualenv (or a container)
    - Run `python3 -m venv .env` in the terminal.

6. Activate your virtualenv
    - Run `source .env/bin/activate` in the terminal.

7. Install the dependencies 
    - Run `./build.sh` in the terminal.
    - Rerun `build.sh` whenever you edit the `child_lambda_function.py`.
    - For more info (https://docs.aws.amazon.com/lambda/latest/dg/python-package.html)

8. Deploy the Stack
    - Run `cdk deploy` in the terminal.

9. After deployment, a `NEWSAPIEndpoint` will be returned as output. Use it to invoke the API
    - To run for all the companies available in `news-research-issuers-table`, run 
        ```
        curl -X POST https://api-gateway-url/run-all
        ```
    - To run for a specific issuer x, run 
        ```
        curl -X POST https://api-gateway-url/run-issuer -d "x"
        ```



## Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation
