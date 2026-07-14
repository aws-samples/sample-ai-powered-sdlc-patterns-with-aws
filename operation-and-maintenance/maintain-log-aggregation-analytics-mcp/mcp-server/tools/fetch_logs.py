"""Fetch logs from CloudWatch Logs."""

import boto3
from botocore.exceptions import ClientError
from datetime import datetime, timedelta, timezone
import re

from .validation import validate_log_group, validate_limit, validate_filter_pattern, ValidationError
from .sanitize import sanitize_aws_error

logs_client = boto3.client('logs')


def parse_time(time_str: str) -> datetime:
    """Parse time string to datetime. Supports ISO format or relative (1h, 30m, 7d)."""
    now = datetime.now(timezone.utc)
    if not time_str or time_str == 'now':
        return now

    # Relative time pattern
    match = re.match(r'^(\d+)([mhd])$', time_str)
    if match:
        value, unit = int(match.group(1)), match.group(2)
        delta = {'m': timedelta(minutes=value), 'h': timedelta(hours=value), 'd': timedelta(days=value)}
        return now - delta[unit]

    return datetime.fromisoformat(time_str.replace('Z', '+00:00'))


async def fetch_logs(args: dict) -> dict:
    """Fetch logs from CloudWatch for a specific log group and time range."""
    try:
        log_group = validate_log_group(args['log_group'])
        limit = validate_limit(args.get('limit', 100))
        filter_pattern = args.get('filter_pattern', '')
        if filter_pattern:
            filter_pattern = validate_filter_pattern(filter_pattern)
    except ValidationError as e:
        return {'error': f'Validation error: {str(e)}', 'count': 0, 'events': []}

    start_time = parse_time(args.get('start_time', '1h'))
    end_time = parse_time(args.get('end_time', 'now'))

    params = {
        'logGroupName': log_group,
        'startTime': int(start_time.timestamp() * 1000),
        'endTime': int(end_time.timestamp() * 1000),
        'limit': limit
    }
    if filter_pattern:
        params['filterPattern'] = filter_pattern

    try:
        response = logs_client.filter_log_events(**params)
    except ClientError as e:
        error_code = e.response['Error']['Code']
        raw_message = e.response['Error']['Message']
        return {
            'error': f"AWS API error ({error_code}): {sanitize_aws_error(raw_message)}",
            'count': 0,
            'events': []
        }

    events = [{
        'timestamp': datetime.fromtimestamp(e['timestamp'] / 1000).isoformat(),
        'message': e['message'],
        'logStream': e.get('logStreamName', '')
    } for e in response.get('events', [])]

    return {
        'log_group': log_group,
        'time_range': {'start': start_time.isoformat(), 'end': end_time.isoformat()},
        'count': len(events),
        'events': events
    }
