"""AI-powered error analysis using Amazon Bedrock."""

import os
import boto3
import json
from botocore.exceptions import ClientError

from .fetch_logs import fetch_logs
from .validation import validate_log_group, validate_time_range, validate_error_type_item, ValidationError
from .sanitize import sanitize_for_bedrock, sanitize_aws_error

bedrock = boto3.client('bedrock-runtime')
logs_client = boto3.client('logs')

MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-3-haiku-20240307-v1:0')

ANALYSIS_PROMPT = """Analyze these application logs and provide:
1. **Error Summary**: List distinct error types with counts
2. **Pattern Detection**: Identify recurring patterns or anomalies
3. **Root Cause Analysis**: Likely causes for each error type
4. **Recommendations**: Specific fixes or next debugging steps

Logs:
{logs}

Provide a structured, actionable analysis."""


async def analyze_errors(args: dict) -> dict:
    """Use Bedrock to analyze log errors and detect patterns."""
    try:
        log_group = validate_log_group(args['log_group'])
        time_range = validate_time_range(args.get('time_range', '1h'))
    except ValidationError as e:
        return {'error': f'Validation error: {str(e)}'}

    error_types = args.get('error_types', [])

    # Build filter for errors
    filter_pattern = '?ERROR ?Error ?error ?WARN ?Exception ?FATAL'
    if error_types:
        try:
            validated = [validate_error_type_item(e) for e in error_types]
        except ValidationError as e:
            return {'error': f'Validation error: {str(e)}'}
        filter_pattern = ' '.join(f'?{e}' for e in validated)

    # Fetch error logs
    log_result = await fetch_logs({
        'log_group': log_group,
        'start_time': time_range,
        'filter_pattern': filter_pattern,
        'limit': 200
    })

    if log_result.get('error'):
        return log_result

    if not log_result['events']:
        return {
            'log_group': log_group,
            'time_range': time_range,
            'status': 'healthy',
            'message': 'No errors found in the specified time range'
        }

    # Prepare and sanitize logs for analysis
    log_text = '\n'.join(f"[{e['timestamp']}] {e['message'][:500]}" for e in log_result['events'][:50])
    log_text = sanitize_for_bedrock(log_text)

    # Call Bedrock for analysis
    try:
        response = bedrock.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps({
                'anthropic_version': 'bedrock-2023-05-31',
                'max_tokens': 1500,
                'messages': [{'role': 'user', 'content': ANALYSIS_PROMPT.format(logs=log_text)}]
            })
        )
        analysis = json.loads(response['body'].read())['content'][0]['text']
    except ClientError as e:
        error_code = e.response['Error']['Code']
        raw_message = e.response['Error']['Message']
        return {
            'log_group': log_group,
            'time_range': log_result['time_range'],
            'error_count': log_result['count'],
            'error': f"Bedrock API error ({error_code}): {sanitize_aws_error(raw_message)}"
        }

    return {
        'log_group': log_group,
        'time_range': log_result['time_range'],
        'error_count': log_result['count'],
        'analysis': analysis
    }
