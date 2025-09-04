const AWS = require('aws-sdk');
const cloudwatch = new AWS.CloudWatch();

exports.handler = async (event) => {
    console.log('Monitoring metrics Lambda triggered:', JSON.stringify(event, null, 2));
    
    try {
        // Put custom metrics to CloudWatch
        const params = {
            Namespace: 'AI-Assistant/Monitoring',
            MetricData: [
                {
                    MetricName: 'HealthCheck',
                    Value: 1,
                    Unit: 'Count',
                    Timestamp: new Date()
                }
            ]
        };
        
        await cloudwatch.putMetricData(params).promise();
        
        return {
            statusCode: 200,
            body: JSON.stringify({
                message: 'Monitoring metrics processed successfully'
            })
        };
    } catch (error) {
        console.error('Error processing monitoring metrics:', error);
        throw error;
    }
};