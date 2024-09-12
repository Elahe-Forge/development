# News Research Project
This AWS-based project operates on a serverless architecture, primarily using S3 and Lambda functions, orchestrated through AWS CDK. The central mechanism involves four Lambda functions: a function that extracts text from an uploaded Certificate of Incorporation (COI) pdf, a function that reads COI's using LLMs to extract data, a function that transforms the extracted data into an Excel workbook, and a function that emails the Excel workbook to our stakeholders. The lambda functions are each triggered when an object is created in S3.

The entire setup is defined and deployed using AWS CDK. See the Miro board for more info and the arch design: https://miro.com/app/board/uXjVNs714WI=/

## Steps to Run

1. Install Python version 3.9 or later

2. Install Node.js and npm
    - AWS CDK is developed in Node.js, so you need to install Node.js and npm.

3. Install AWS Command Line Interface (CLI)
    - Once installed, configure it by running:
        - non-production: `aws configure --profile dev`
        
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

## Useful commands

 * `cat ~/.aws/credentials`  lists the credentials set for each profile:
 * `cdk ls`          lists all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation