# Security Policy

## Reporting Vulnerabilities

If you discover a potential security issue in this project, please report it through the
[AWS Vulnerability Reporting](https://aws.amazon.com/security/vulnerability-reporting/) page.

Please do **not** create a public GitHub issue for security vulnerabilities.

## Deployment Security Best Practices

### IAM Permissions
- Follow the principle of least privilege. Use the IAM policy in the README as a starting point and scope it to your specific resources and region.
- Restrict `Resource: "*"` statements with `Condition` keys (e.g., `aws:RequestedRegion`) where resource-level permissions are not supported.
- Use separate IAM roles for the MCP server and the sample application.

### Credentials
- Never hardcode AWS credentials. Use IAM roles, environment variables, or AWS credential profiles.
- Rotate credentials regularly and use temporary credentials (STS) where possible.

### VPC and Network
- For production use, consider running the MCP server within a VPC with VPC endpoints for AWS services (CloudWatch, X-Ray, Bedrock) to avoid traffic traversing the public internet.
- Restrict API Gateway access using resource policies, IAM authorization, or API keys.

## Data Security

### Log Sanitization
- The MCP server sanitizes log data before sending it to Amazon Bedrock, stripping patterns matching AWS access keys, secrets, bearer tokens, email addresses, and IP addresses.
- A maximum character limit is enforced on text sent to the model to prevent excessive data exposure.
- Review the sanitization patterns in `mcp-server/tools/sanitize.py` and extend them for your environment.

### Encryption
- The sample DynamoDB table uses AWS-managed encryption at rest.
- All AWS API calls use TLS in transit.
- Amazon Bedrock processes data in accordance with the [AWS Shared Responsibility Model](https://aws.amazon.com/compliance/shared-responsibility-model/).

### Amazon Bedrock Data Handling
- Log data sent to Amazon Bedrock for analysis is not used to train models.
- Review the [Amazon Bedrock data privacy FAQ](https://aws.amazon.com/bedrock/faqs/) for details.

## Known Security Considerations

- This is a sample/demo application. The sample Lambda intentionally simulates errors and is not intended for production use.
- The API Gateway endpoint is publicly accessible by default. Add authorization for any non-demo deployment.
- The MCP server runs locally and communicates with AWS services using your configured credentials.

## Production Recommendations

1. Enable API Gateway authorization (IAM, Cognito, or Lambda authorizer)
2. Deploy within a VPC with private subnets and VPC endpoints
3. Enable AWS CloudTrail for auditing API calls
4. Set up CloudWatch Alarms for error rate and latency thresholds
5. Review and extend the log sanitization patterns for your specific data
6. Use AWS Secrets Manager for any additional secrets

## Acknowledgments

- Abhishek Agawane ([agawanea@amazon.com](mailto:agawanea@amazon.com)) — Security review and threat modeling (PCSR).

