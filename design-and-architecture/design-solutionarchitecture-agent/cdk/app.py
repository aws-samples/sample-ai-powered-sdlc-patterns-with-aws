#!/usr/bin/env python3
import os

import aws_cdk as cdk
from stack.stack import AWSAgentStack

app = cdk.App()
AWSAgentStack(app, "AWSAgentStack",
    env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION'))
)

app.synth()
