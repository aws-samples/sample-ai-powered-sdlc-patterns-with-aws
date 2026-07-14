"""Trace requests across services using X-Ray and correlate logs."""

import os
import boto3
import json
from botocore.exceptions import ClientError
from datetime import datetime, timedelta

from .validation import (
    validate_trace_id, validate_time_range, validate_request_id,
    LOG_GROUP_ALLOWLIST, ValidationError
)
from .sanitize import sanitize_for_bedrock, sanitize_aws_error
from .fetch_logs import parse_time

xray = boto3.client('xray')
logs_client = boto3.client('logs')
bedrock = boto3.client('bedrock-runtime')

MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'anthropic.claude-3-haiku-20240307-v1:0')


async def trace_request(args: dict) -> dict:
    """Trace a request across services and correlate logs."""
    trace_id = args.get('trace_id')
    request_id = args.get('request_id')
    time_range = args.get('time_range', '1h')

    if not trace_id and not request_id:
        return {'error': 'Provide either trace_id or request_id'}

    try:
        if trace_id:
            trace_id = validate_trace_id(trace_id)
        if request_id:
            request_id = validate_request_id(request_id)
        time_range = validate_time_range(time_range)
    except ValidationError as e:
        return {'error': f'Validation error: {str(e)}'}

    result = {'trace_id': trace_id, 'request_id': request_id, 'services': []}

    # Get X-Ray trace if trace_id provided
    if trace_id:
        try:
            trace_resp = xray.batch_get_traces(TraceIds=[trace_id])
            if trace_resp.get('Traces'):
                trace = trace_resp['Traces'][0]
                for segment in trace.get('Segments', []):
                    doc = json.loads(segment['Document'])
                    result['services'].append({
                        'name': doc.get('name'),
                        'duration_ms': (doc.get('end_time', 0) - doc.get('start_time', 0)) * 1000,
                        'error': doc.get('error', False),
                        'fault': doc.get('fault', False)
                    })
        except ClientError as e:
            error_code = e.response['Error']['Code']
            raw_message = e.response['Error']['Message']
            result['trace_error'] = f"AWS API error ({error_code}): {sanitize_aws_error(raw_message)}"
        except Exception as e:
            result['trace_error'] = sanitize_aws_error(str(e))

    # Search logs for request_id across log groups (respects LOG_GROUP_ALLOWLIST)
    if request_id:
        result['correlated_logs'] = []
        try:
            log_groups = logs_client.describe_log_groups(limit=10)
            start_time = parse_time(time_range)
            end_time = datetime.utcnow()

            for lg in log_groups.get('logGroups', [])[:5]:
                lg_name = lg['logGroupName']

                # Enforce the same allowlist that fetch_logs uses
                if LOG_GROUP_ALLOWLIST:
                    if not any(lg_name.startswith(prefix) for prefix in LOG_GROUP_ALLOWLIST):
                        continue

                events = logs_client.filter_log_events(
                    logGroupName=lg_name,
                    filterPattern=f'"{request_id}"',
                    startTime=int(start_time.timestamp() * 1000),
                    endTime=int(end_time.timestamp() * 1000),
                    limit=10
                )
                for e in events.get('events', []):
                    result['correlated_logs'].append({
                        'log_group': lg_name,
                        'timestamp': datetime.fromtimestamp(e['timestamp'] / 1000).isoformat(),
                        'message': e['message'][:300]
                    })
        except ClientError as e:
            error_code = e.response['Error']['Code']
            raw_message = e.response['Error']['Message']
            result['log_error'] = f"AWS API error ({error_code}): {sanitize_aws_error(raw_message)}"
        except Exception as e:
            result['log_error'] = sanitize_aws_error(str(e))

    # AI summary if we have data
    if result['services'] or result.get('correlated_logs'):
        summary_data = sanitize_for_bedrock(
            f"Services: {json.dumps(result['services'])}\n"
            f"Logs: {json.dumps(result.get('correlated_logs', [])[:10])}"
        )
        summary_prompt = f"Summarize this request trace and identify any issues:\n{summary_data}"
        try:
            resp = bedrock.invoke_model(
                modelId=MODEL_ID,
                body=json.dumps({
                    'anthropic_version': 'bedrock-2023-05-31',
                    'max_tokens': 500,
                    'messages': [{'role': 'user', 'content': summary_prompt}]
                })
            )
            result['ai_summary'] = json.loads(resp['body'].read())['content'][0]['text']
        except ClientError as e:
            error_code = e.response['Error']['Code']
            raw_message = e.response['Error']['Message']
            result['ai_summary_error'] = f"Bedrock API error ({error_code}): {sanitize_aws_error(raw_message)}"
        except Exception as e:
            result['ai_summary_error'] = f"AI summary unavailable: {sanitize_aws_error(str(e))}"

    return result
