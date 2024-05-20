
# News Research Project
This AWS-based project operates on a serverless architecture, primarily using Lambda functions and SQS, orchestrated through AWS CDK. The central mechanism involves three Lambda functions: a function that gets the name of companies (issuers) from Athena, a function that fetches news for each issuer using SerpAPI, and a function that summarizes the news (adds tags, etc) using LLM. These tasks are implemented using SQS queues. 
The entire setup is defined and deployed using AWS CDK. See the Miro board for more info and the arch design: https://miro.com/app/board/uXjVNP-1p2E=/

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
    - Run `pip install -r requirements.txt` in the terminal.

8. Make sure the Docker is up and running

9. Deploy the Stack
    - To deploy a specific stack: `cdk deploy news-research`
    - To deploy multiple specific stacks: `cdk deploy news-research news-evaluation`
    - To deploy all stacks in the app: `cdk deploy --all`

10. After deployment, a `NEWSAPIEndpoint` will be returned as output. Use it to invoke the API
    - To run for all the issuers available in an athena table, run 
        ```
        curl -X POST https://api-gateway-url/run-all
        ```
    - To run for a specific issuer x, run 
        ```
        curl -X POST https://api-gateway-url/run-issuer -d "x"
        ```
    - To run for all issuers available in Excel file in folder x in S3 bucket `data-science-news-issuer-list`, run 
        ```
        curl -X POST https://api-gateway-url/run-s3 -d "x"
        ```

11. The news articles exist as Parquet files in S3 bucket `data-science-news-output`



## Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation
