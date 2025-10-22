# DevOps AI Assistant: Streamline Your Development and Deployment Workflows

## Introduction

The DevOps AI Assistant is a comprehensive tool that automates various aspects of DevOps processes, from generating Dockerfiles (using Finch) to creating infrastructure as code for both ECS and EKS using Terraform and CloudFormation.

This AI-powered assistant streamlines development and deployment workflows by leveraging advanced code generation techniques. It supports multiple container orchestration platforms and aims to minimize manual coding, reduce errors, and enhance the overall efficiency of DevOps practices.

## Solution Architecture

The DevOps AI Assistant follows a modular architecture with AI-powered code generation at its core:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   User Input    │───▶│  Streamlit UI    │───▶│ Project Analysis│
│ (Git Repo/Code) │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Generated     │◀───│  AWS Bedrock     │◀───│ Code Generation │
│   Artifacts     │    │   AI Models      │    │   Templates     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Architecture Steps:

1. **Input Processing**: User provides Git repository URL or code requirements
2. **Project Analysis**: AI identifies project type, language, and framework
3. **Template Selection**: System selects appropriate generation templates
4. **AI Code Generation**: AWS Bedrock models generate infrastructure code
5. **Validation**: Generated code is validated for syntax and best practices
6. **Output Display**: Results shown in Streamlit UI with syntax highlighting
7. **Optional Execution**: Generated code can be executed (Docker build, Terraform plan)

### Supported Outputs:
- **Dockerfiles**: Optimized container definitions
- **Terraform**: ECS/EKS infrastructure as code
- **CloudFormation**: AWS infrastructure templates
- **BuildSpec**: CI/CD pipeline configurations
- **Kubernetes Manifests**: Container orchestration definitions

## Prerequisites

Before using the DevOps AI Assistant, ensure you have:

### Required Software:
- **Python 3.7+**: Runtime environment
- **Finch**: Container building and testing
- **AWS CLI**: AWS service interactions
- **Git**: Repository cloning (optional)

### AWS Configuration:
- **AWS Account**: Active AWS account with appropriate permissions
- **AWS CLI Configured**: Run `aws configure` with your credentials
- **Required AWS Permissions**:
  - Amazon Bedrock access (for AI models)
  - ECR access (for container registry)
  - ECS/EKS permissions (for infrastructure deployment)
  - CloudFormation/Terraform execution permissions

### Environment Setup:
- **Internet Connection**: Required for AI model access and package installation
- **Sufficient Disk Space**: For Docker images and generated artifacts
- **Port 8501**: Available for Streamlit application (default)

## Deployment Instructions

### 1. Clone Repository
```bash
git clone <repository-url>
cd automated-devops-ai-toolkit
```

### 2. Environment Setup
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate     # Windows
```

### 3. Install Dependencies
```bash
pip3 install -r requirements.txt
```

### 4. Configure AWS
```bash
# Configure AWS CLI (if not already done)
aws configure

# Verify AWS access
aws sts get-caller-identity
```

### 5. Launch Application
```bash
streamlit run app.py
```

### 6. Access Application
- Open browser to: `http://localhost:8501`
- Navigate using sidebar menu
- Start with Dockerfile generation for testing

## Test

### Basic Functionality Test

1. **Dockerfile Generation Test**:
   ```bash
   # Use sample repository
   Repository URL: https://github.com/<sample-app-code-repository>
   ```
   - Expected: Generated Dockerfile for Java Spring application or Golang Applicaion etc
   - Verify: Dockerfile contains appropriate Java or Golang base image and build steps for example

2. **ECS Terraform Test**:
   - Input: Generated Dockerfile from step 1
   - Select: Fargate deployment type
   - Expected: Complete Terraform configuration with VPC, ECS cluster, and task definition

3. **EKS CloudFormation Test**:
   - Input: Same Dockerfile
   - Select: EKS Fargate deployment
   - Expected: CloudFormation template with EKS cluster and Kubernetes manifests

### Validation Tests

```bash
# Test generated Terraform
cd iac/
terraform init
terraform validate
terraform plan

# Test generated CloudFormation
aws cloudformation validate-template --template-body file://template.yaml

# Test generated Docker image
finch  build -t test-app . # solution used Finch
finch run --rm test-app.   # solution used Finch
```

## Clean Up

### Application Cleanup
```bash
# Stop Streamlit application
Ctrl+C

# Deactivate virtual environment
deactivate

# Remove virtual environment (optional)
rm -rf venv
```

### AWS Resources Cleanup

#### Terraform Resources:
```bash
cd iac/
terraform destroy
```

#### CloudFormation Resources:
```bash
# List stacks
aws cloudformation list-stacks

# Delete specific stack
aws cloudformation delete-stack --stack-name <stack-name>
```

#### Docker Cleanup:
```bash
# Remove generated images
docker rmi $(docker images -q)

# Clean up Docker system
docker system prune -a
```

#### ECR Cleanup:
```bash
# List repositories
aws ecr describe-repositories

# Delete repository
aws ecr delete-repository --repository-name <repo-name> --force
```

### File Cleanup:
```bash
# Remove generated files
rm -rf iac/
rm -rf temp_repo/
rm -f Dockerfile
```

## Repository Structure

- `app/`: Main application directory
  - `core/`: Core functionality modules
    - `bedrock_definition.py`: AWS Bedrock model configuration
    - `build_docker_image.py`: Docker image building logic
    - `custom_logging.py`: Logging configuration
    - `identify_project.py`: Project identification logic
    - `dockerfile_validator.py`: Dockerfile validation utilities
  - `generators/`: Code generation modules
    - `buildspec/`: BuildSpec generation
    - `cloudformation/`: CloudFormation template generation (ECS & EKS)
    - `docker/`: Dockerfile generation
    - `terraform/`: Terraform configuration generation (ECS & EKS)
  - `pages/`: Streamlit pages for different functionalities
    - `1_dockerfile_generation.py`: Docker container generation
    - `2_terraform_generation.py`: ECS Terraform infrastructure
    - `3_cloudformation_generation.py`: ECS CloudFormation infrastructure
    - `4_buildspec_generation.py`: CI/CD pipeline configuration
    - `5_eks_terraform_generation.py`: EKS Terraform infrastructure
    - `6_eks_cloudformation_generation.py`: EKS CloudFormation infrastructure
  - `app.py`: Main Streamlit application entry point

## Authors and acknowledgment
We would like to thank the following contributors for their valuable input and work on this project _(sorted alphabetically)_:

• Aditya Ambati 

• Anand Krishna Varanasi 

• JAGDISH KOMAKULA 

• Sarat Chandra Pothula 

• T.V.R.L.Phani Kumar Dadi 

• Varun Sharma


## Usage Instructions

### Installation

Prerequisites:
- Python 3.7+
- Docker
- AWS CLI configured with appropriate permissions

Steps:
1. Clone the repository:
   ```
   git clone <repository-url>
   cd devops-ai-assistant
   ```
2. Create and activate a virtual environment:
   ```
   python3 -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```
3. Install dependencies:
   ```
   pip3 install -r requirements.txt
   ```

### Getting Started

1. Run the Streamlit application:
   ```
   streamlit run app.py
   ```
2. Open your web browser and navigate to the URL displayed in the terminal.

3. Use the sidebar to navigate between different functionalities:
   - **Dockerfile Generation:** Create optimized Docker containers
   - **ECS Terraform Generation:** AWS ECS infrastructure with Terraform
   - **ECS CloudFormation Generation:** AWS ECS infrastructure with CloudFormation
   - **BuildSpec Generation:** CI/CD pipeline configuration
   - **EKS Terraform Generation:** AWS EKS infrastructure with Terraform
   - **EKS CloudFormation Generation:** AWS EKS infrastructure with CloudFormation

### Configuration Options

- AWS Credentials: Ensure your AWS CLI is configured with the necessary permissions for Bedrock, ECR, and other AWS services used by the application.
- Model Configuration: Adjust the Bedrock model settings in `app/core/bedrock_definition.py` if needed.

### Common Use Cases

1. **Dockerfile Generation:**
   - Input: Git repository URL
   - Output: Generated Dockerfile and built Docker image

2. **ECS Infrastructure Generation:**
   - **Terraform for ECS:** Fargate and EC2 Auto Scaling configurations
   - **CloudFormation for ECS:** Complete ECS infrastructure templates

3. **EKS Infrastructure Generation:**
   - **Terraform for EKS:** Fargate and EC2 Node Group configurations  
   - **CloudFormation for EKS:** Complete EKS infrastructure templates

4. **BuildSpec Generation:**
   - Input: ECR repository name and URI
   - Output: BuildSpec YAML file for AWS CodeBuild

### Troubleshooting

- If you encounter issues with AWS services, ensure your AWS CLI is properly configured and you have the necessary permissions.
- For Docker-related issues, make sure Docker/Finch is running and you have the required permissions to build and run containers.
- Check the application logs for detailed error messages and stack traces.

## Data Flow

The DevOps AI Assistant processes user inputs through a series of AI-powered generation steps:

1. User provides input (e.g., Git repository URL, infrastructure requirements)
2. Application identifies project type and structure
3. AI model generates appropriate code (Dockerfile, Terraform, CloudFormation, or BuildSpec)
4. Generated code is validated and optionally executed
5. Results are displayed to the user with error handling and feedback

```
[User Input] -> [Project Identification] -> [AI Code Generation] -> [Validation] -> [Output Display/Execution]
```

### Container Orchestration Options

#### AWS ECS (Elastic Container Service)
- **Fargate**: Serverless container execution
- **EC2 Auto Scaling**: Managed EC2 instances with auto scaling

#### AWS EKS (Elastic Kubernetes Service)
- **Fargate**: Serverless Kubernetes pods
- **EC2 Node Groups**: Managed EC2 instances for Kubernetes nodes

Key components in the data flow:
- **Bedrock AI model**: Handles code generation based on prompts and templates
- **Dockerfile Validator**: Ensures generated Dockerfiles are valid and properly formatted
- **Streamlit UI**: Manages user interactions and displays results
- **Finch**: Builds and tests generated Dockerfiles
- **AWS services**: Interact with ECR, ECS, EKS, and other AWS resources as needed


## Demo of the Solution

[![Demo](sample-ai-powered-sdlc-patterns-with-aws/deployment/deploy-devops-ai-assistant/demo/demo-devops-ai-assistant2.mov)

## Disclaimer

The solution architecture sample code is provided without any guarantees, and you're not recommended to use it for production-grade workloads. The intention is to provide content to build and learn. Be sure of reading the licensing terms.

## License
MIT-0
