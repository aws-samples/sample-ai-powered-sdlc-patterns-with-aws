"""Check metrics against SLA thresholds."""

import boto3
from botocore.exceptions import ClientError
from datetime import datetime, timedelta

from .validation import (
    validate_service_name, validate_metric_type, validate_time_range,
    validate_threshold, ValidationError
)
from .sanitize import sanitize_aws_error
from .fetch_logs import parse_time

cloudwatch = boto3.client('cloudwatch')


async def check_sla(args: dict) -> dict:
    """Check CloudWatch metrics against SLA thresholds."""
    try:
        service_name = validate_service_name(args['service_name'])
        metric_type = validate_metric_type(args['metric_type'])
        time_range = validate_time_range(args.get('time_range', '24h'))
        threshold = validate_threshold(args['threshold'])
    except ValidationError as e:
        return {'error': f'Validation error: {str(e)}'}

    # Parse time range using shared utility
    start_time = parse_time(time_range)
    end_time = datetime.utcnow()

    # Map metric types to CloudWatch metrics
    metric_config = {
        'latency': {'MetricName': 'Duration', 'Namespace': 'AWS/Lambda', 'Stat': 'p99'},
        'error_rate': {'MetricName': 'Errors', 'Namespace': 'AWS/Lambda', 'Stat': 'Sum'},
        'availability': {'MetricName': 'Invocations', 'Namespace': 'AWS/Lambda', 'Stat': 'Sum'}
    }

    config = metric_config[metric_type]

    # Get metric data
    params = {
        'Namespace': config['Namespace'],
        'MetricName': config['MetricName'],
        'Dimensions': [{'Name': 'FunctionName', 'Value': service_name}],
        'StartTime': start_time,
        'EndTime': end_time,
        'Period': 3600,
        'Statistics': ['Sum', 'Average']
    }
    if config['Stat'] == 'p99':
        params['ExtendedStatistics'] = ['p99']

    try:
        response = cloudwatch.get_metric_statistics(**params)
    except ClientError as e:
        error_code = e.response['Error']['Code']
        raw_message = e.response['Error']['Message']
        return {
            'error': f"AWS API error ({error_code}): {sanitize_aws_error(raw_message)}",
            'service': service_name,
            'metric': metric_type
        }

    datapoints = response.get('Datapoints', [])
    if not datapoints:
        return {
            'service': service_name,
            'metric': metric_type,
            'status': 'no_data',
            'message': 'No metric data available for the specified time range'
        }

    # Calculate actual value based on metric type
    if metric_type == 'latency':
        values = [dp.get('ExtendedStatistics', {}).get('p99', dp.get('Average', 0)) for dp in datapoints]
        actual_value = max(values) if values else 0
        unit = 'ms'
        compliant = actual_value <= threshold
    elif metric_type == 'error_rate':
        total_errors = sum(dp.get('Sum', 0) for dp in datapoints)
        try:
            invocations = cloudwatch.get_metric_statistics(
                Namespace='AWS/Lambda', MetricName='Invocations',
                Dimensions=[{'Name': 'FunctionName', 'Value': service_name}],
                StartTime=start_time, EndTime=end_time, Period=3600, Statistics=['Sum']
            )
        except ClientError as e:
            error_code = e.response['Error']['Code']
            raw_message = e.response['Error']['Message']
            return {
                'error': f"AWS API error ({error_code}): {sanitize_aws_error(raw_message)}",
                'service': service_name,
                'metric': metric_type
            }
        total_invocations = sum(dp.get('Sum', 0) for dp in invocations.get('Datapoints', []))
        actual_value = (total_errors / total_invocations * 100) if total_invocations > 0 else 0
        unit = '%'
        compliant = actual_value <= threshold
    else:  # availability
        total_invocations = sum(dp.get('Sum', 0) for dp in datapoints)
        actual_value = 100 if total_invocations > 0 else 0
        unit = '%'
        compliant = actual_value >= threshold

    return {
        'service': service_name,
        'metric': metric_type,
        'threshold': f'{threshold}{unit}',
        'actual': f'{actual_value:.2f}{unit}',
        'compliant': compliant,
        'status': 'PASS' if compliant else 'FAIL',
        'time_range': {'start': start_time.isoformat(), 'end': end_time.isoformat()},
        'datapoints_analyzed': len(datapoints)
    }
