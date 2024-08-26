
# S1 Filings Project

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




## Useful commands

 * `cat ~/.aws/credentials`  lists the credentials set for each profile:
 * `cdk ls`          lists all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation
