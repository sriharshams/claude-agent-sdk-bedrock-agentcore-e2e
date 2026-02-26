# Deploy to AgentCore Runtime

## Prerequisites
- Docker installed and running
- AWS CLI configured with appropriate permissions
- ECR repository created or auto-create enabled
- IAM execution role for AgentCore Runtime

## Deployment Steps

### 1. Build Docker Image
```bash
docker build -t customer-support-agent -f runtime/Dockerfile .
```

### 2. Tag and Push to ECR
```bash
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region)
ECR_REPO="${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com/customer-support-agent"

aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REPO}
docker tag customer-support-agent:latest ${ECR_REPO}:latest
docker push ${ECR_REPO}:latest
```

### 3. Deploy to AgentCore Runtime
Use the `bedrock-agentcore-starter-toolkit` Runtime class:
```python
from bedrock_agentcore_starter_toolkit import Runtime
runtime = Runtime()
runtime.configure(entrypoint="runtime/app.py", execution_role=role_arn, ...)
runtime.launch(env_vars={"MEMORY_ID": memory_id, "CLAUDE_CODE_USE_BEDROCK": "1"})
```

### 4. Verify Deployment
```python
status = runtime.status()
print(f"Status: {status.endpoint['status']}")
# Should show "READY"
```

## Environment Variables
- `CLAUDE_CODE_USE_BEDROCK=1` - Use Bedrock as backend (required)
- `MEMORY_ID` - AgentCore Memory resource ID
- `AWS_DEFAULT_REGION` - AWS region

## IAM Role Requirements
- ECR image pull access
- Bedrock model invocation
- AgentCore Memory read/write
- AgentCore Gateway access
- SSM Parameter Store read
- CloudWatch Logs write
- X-Ray trace submission
