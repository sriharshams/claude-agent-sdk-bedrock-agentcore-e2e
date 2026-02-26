# Troubleshooting Guide

## Common Agent Errors

### "CLAUDE_CODE_USE_BEDROCK not set"
- Ensure `export CLAUDE_CODE_USE_BEDROCK=1` is set in your environment
- For Docker: add `ENV CLAUDE_CODE_USE_BEDROCK=1` to Dockerfile

### "Access denied" on Bedrock model invocation
- Verify model access is enabled in the AWS Bedrock console
- Check IAM role has `bedrock:InvokeModel` and `bedrock:InvokeModelWithResponseStream`
- Ensure the model ID is correct: `global.anthropic.claude-haiku-4-5-20251001-v1:0`

### Memory retrieval returns empty results
- Verify memory resource exists: check SSM parameter `/app/customersupport/agentcore/memory_id`
- Ensure events have been created and LTM processing has completed (can take a few minutes)
- Check namespace format matches: `support/customer/{actorId}/semantic`

### Gateway connection refused
- Verify gateway URL from SSM parameter `/app/customersupport/agentcore/gateway_id`
- Ensure JWT token is valid and not expired
- Check Cognito client ID matches gateway authorizer configuration

### Runtime deployment fails
- Check ECR repository exists and image was pushed successfully
- Verify execution role ARN and permissions
- Check CloudWatch logs: `/aws/bedrock-agentcore/runtimes/*`

## Debugging Commands

### Check SSM parameters
```bash
aws ssm get-parameters-by-path --path /app/customersupport --recursive --with-decryption --output table
```

### Check runtime status
```python
import boto3
client = boto3.client("bedrock-agentcore-control")
runtimes = client.list_agent_runtimes()
for rt in runtimes["agentRuntimes"]:
    print(f"{rt['agentRuntimeId']}: {rt['status']}")
```

### Check gateway status
```python
import boto3
client = boto3.client("bedrock-agentcore-control")
gateways = client.list_gateways()
for gw in gateways["items"]:
    print(f"{gw['gatewayId']}: {gw['status']}")
```

### View CloudWatch logs
```bash
aws logs tail /aws/bedrock-agentcore/runtimes/<runtime-id> --follow
```

## Performance Optimization
- Use `max_turns=10` to limit agent reasoning depth
- Set `temperature=0.3` for more deterministic responses
- Use `allowed_tools` to restrict tool access when not all tools are needed
- Enable streaming for better user experience in frontend
