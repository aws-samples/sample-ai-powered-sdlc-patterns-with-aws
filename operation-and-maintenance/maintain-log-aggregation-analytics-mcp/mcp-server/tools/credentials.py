"""AWS credential safety checks.

Validates that the MCP server is running with appropriately scoped
credentials — preferring temporary (STS) sessions over long-lived
access keys, and warning when overly permissive policies are detected.
"""

import os
import logging
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

logger = logging.getLogger("mcp.credentials")

# Actions this server actually needs — nothing more
REQUIRED_ACTIONS = frozenset({
    "logs:FilterLogEvents",
    "logs:DescribeLogGroups",
    "logs:GetLogEvents",
    "cloudwatch:GetMetricStatistics",
    "cloudwatch:GetMetricData",
    "xray:BatchGetTraces",
    "xray:GetTraceSummaries",
    "bedrock:InvokeModel",
})

# Dangerous policy patterns that indicate over-provisioning
OVERLY_PERMISSIVE_PATTERNS = [
    "AdministratorAccess",
    "PowerUserAccess",
    "IAMFullAccess",
    "*",  # wildcard action
]


def check_credentials() -> dict:
    """Validate AWS credentials and return a safety report.

    Returns a dict with:
      - valid: bool — whether credentials are configured and working
      - credential_type: 'temporary' | 'long_lived' | 'none'
      - warnings: list[str] — security warnings
      - identity: dict — caller identity info (sanitized)
    """
    report = {
        "valid": False,
        "credential_type": "none",
        "warnings": [],
        "identity": {},
    }

    sts = boto3.client("sts")

    # 1. Check that credentials exist and are valid
    try:
        identity = sts.get_caller_identity()
    except NoCredentialsError:
        report["warnings"].append(
            "No AWS credentials found. Configure credentials via "
            "AWS SSO, environment variables, or ~/.aws/credentials."
        )
        return report
    except ClientError as e:
        report["warnings"].append(f"AWS credentials are invalid: {e.response['Error']['Code']}")
        return report

    report["valid"] = True
    arn = identity.get("Arn", "")
    report["identity"] = {
        "arn_type": _classify_arn(arn),
        "user_id": identity.get("UserId", ""),
    }

    # 2. Check if using temporary credentials (preferred) vs long-lived keys
    #    Temporary creds from STS have a session token; long-lived IAM user keys don't.
    session = boto3.Session()
    creds = session.get_credentials()
    if creds:
        resolved = creds.get_frozen_credentials()
        if resolved.token:
            report["credential_type"] = "temporary"
        else:
            report["credential_type"] = "long_lived"
            report["warnings"].append(
                "Using long-lived AWS access keys. Prefer temporary credentials "
                "via AWS SSO (aws sso login), IAM Identity Center, or "
                "STS AssumeRole for better security."
            )

    # 3. Check if the role/user has overly permissive policies
    if "assumed-role" in arn:
        _check_role_policies(arn, report)
    elif ":user/" in arn:
        _check_user_policies(arn, report)

    # 4. Warn if REQUIRE_TEMP_CREDENTIALS is set and creds are long-lived
    if os.environ.get("REQUIRE_TEMP_CREDENTIALS", "").lower() in ("1", "true", "yes"):
        if report["credential_type"] == "long_lived":
            report["warnings"].append(
                "REQUIRE_TEMP_CREDENTIALS is set but long-lived keys are in use. "
                "The server will still run, but this violates your security policy."
            )

    return report


def _classify_arn(arn: str) -> str:
    """Classify the ARN type for logging (without exposing the full ARN)."""
    if "assumed-role" in arn:
        return "assumed-role"
    elif ":user/" in arn:
        return "iam-user"
    elif ":root" in arn:
        return "root"
    return "unknown"


def _check_role_policies(arn: str, report: dict) -> None:
    """Check attached policies on the assumed role for over-provisioning."""
    try:
        # Extract role name from assumed-role ARN
        # Format: arn:aws:sts::ACCOUNT:assumed-role/ROLE_NAME/SESSION
        parts = arn.split("/")
        if len(parts) < 2:
            return
        role_name = parts[1]

        iam = boto3.client("iam")
        attached = iam.list_attached_role_policies(RoleName=role_name)
        for policy in attached.get("AttachedPolicies", []):
            policy_name = policy.get("PolicyName", "")
            if any(pattern in policy_name for pattern in OVERLY_PERMISSIVE_PATTERNS):
                report["warnings"].append(
                    f"Role has overly permissive policy: {policy_name}. "
                    "Use the least-privilege IAM policy from the README instead."
                )
    except ClientError:
        # Can't check policies — might not have iam:ListAttachedRolePolicies
        # That's fine, it's a best-effort check
        pass


def _check_user_policies(arn: str, report: dict) -> None:
    """Check attached policies on the IAM user for over-provisioning."""
    try:
        parts = arn.split("/")
        if len(parts) < 2:
            return
        user_name = parts[-1]

        iam = boto3.client("iam")
        attached = iam.list_attached_user_policies(UserName=user_name)
        for policy in attached.get("AttachedPolicies", []):
            policy_name = policy.get("PolicyName", "")
            if any(pattern in policy_name for pattern in OVERLY_PERMISSIVE_PATTERNS):
                report["warnings"].append(
                    f"IAM user has overly permissive policy: {policy_name}. "
                    "Use the least-privilege IAM policy from the README instead."
                )
    except ClientError:
        pass
