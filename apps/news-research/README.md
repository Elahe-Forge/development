
# News Research Project
This AWS-based project operates on a serverless architecture, primarily using Lambda functions and SQS, orchestrated through AWS CDK. The central mechanism involves three Lambda functions: a function that gets the name of companies (issuers) from Athena, a function that fetches news for each issuer using SerpAPI, and a function that summarizes the news (adds tags, etc) using LLM. These tasks are implemented using SQS queues. 
The entire setup is defined and deployed using AWS CDK. See the Miro board for more info and the arch design: https://miro.com/app/board/uXjVNP-1p2E=/

## Steps to Run

1. Install Python version 3.9 or later

2. Install Node.js and npm
    - AWS CDK is developed in Node.js, so you need to install Node.js and npm.

3. Install AWS Command Line Interface (CLI)
    - Once installed, configure it by running:
        - non-production: `aws configure --profile dev`
        -  production: `aws configure --profile prod`
        
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
    - Deploy to Development Environment: `./deploy-dev.sh`
    - Deploy to Production Environment: `./deploy-prod.sh`

10. After deployment, a `NEWSAPIEndpoint` will be returned as `data-science-news-automation-dev.NewsApiURL`. Use it to invoke the API. You can also customize (optional) the number of news articles (default is 10) and getting the summary (default is true).
    
    - To run for all issuers available in Excel file in folder x in S3 bucket `data-science-news-issuer-list`, run 
        ```
        curl -X POST "data-science-news-automation-dev.NewsApiURL/run-s3?number_of_articles=10&get_summary=true" -d "x"
        ```
    - To run for issuers that are passed using the JSON data directly via the command line, run 
        ```
        curl -X POST "https://a9g9nnt3zb.execute-api.us-west-2.amazonaws.com/prod/run-json?number_of_articles=10&get_summary=true" \-H "Content-Type: application/json" \-d '[{ "slug": "azul", "name": "Azul", "company_id": "FRG182554" },{ "slug": "oberia", "name": "Oberia", "company_id": "FRG182556" },{ "slug": "autonomous-supersonics", "name": "Autonomous Supersonics", "company_id": "FRG182559" }]'
        ```
    

11. The news articles will be published as Parquet files in S3 bucket `data-science-news-output`



## Useful commands

 * `cat ~/.aws/credentials`  lists the credentials set for each profile:
 * `cdk ls`          lists all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation
