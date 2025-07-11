#!/bin/bash

# AWS Elastic Beanstalk Deployment Script for Java 21 Application
# Cost: ~$40-55/month

echo "🌱 Deploying Java 21 App to AWS Elastic Beanstalk"
echo "================================================="

# Configuration
APP_NAME="java21-modernized-app"
ENV_NAME="java21-production"
REGION="us-east-1"
PLATFORM="64bit Amazon Linux 2023 v4.3.0 running Corretto 21"
INSTANCE_TYPE="t3.small"

echo "📋 Configuration:"
echo "   Application: $APP_NAME"
echo "   Environment: $ENV_NAME"
echo "   Region: $REGION"
echo "   Platform: $PLATFORM"
echo "   Instance Type: $INSTANCE_TYPE"

# Check prerequisites
if ! command -v eb &> /dev/null; then
    echo "❌ EB CLI is required but not installed."
    echo "Install with: pip install awsebcli"
    exit 1
fi

if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ AWS CLI not configured. Please run 'aws configure' first."
    exit 1
fi

echo "🏗️  Step 1: Preparing application for Elastic Beanstalk..."
cd ../java21-app

# Create .ebextensions directory for configuration
mkdir -p .ebextensions

# Create Java configuration
cat > .ebextensions/java.config << EOF
option_settings:
  aws:elasticbeanstalk:application:environment:
    SERVER_PORT: 5000
    SPRING_PROFILES_ACTIVE: production
  aws:elasticbeanstalk:container:java:
    JVMOptions: '-Xmx1g -Xms512m'
    JVMArch: x86_64
  aws:autoscaling:launchconfiguration:
    InstanceType: $INSTANCE_TYPE
    IamInstanceProfile: aws-elasticbeanstalk-ec2-role
  aws:autoscaling:asg:
    MinSize: 1
    MaxSize: 4
  aws:elasticbeanstalk:environment:
    LoadBalancerType: application
  aws:elbv2:loadbalancer:
    IdleTimeout: 60
EOF

# Create health check configuration
cat > .ebextensions/health.config << EOF
option_settings:
  aws:elasticbeanstalk:healthreporting:system:
    SystemType: enhanced
  aws:elasticbeanstalk:application:
    Application Healthcheck URL: /actuator/health
EOF

# Create logging configuration
cat > .ebextensions/logging.config << EOF
option_settings:
  aws:elasticbeanstalk:cloudwatch:logs:
    StreamLogs: true
    DeleteOnTerminate: false
    RetentionInDays: 7
  aws:elasticbeanstalk:cloudwatch:logs:health:
    HealthStreamingEnabled: true
    DeleteOnTerminate: false
    RetentionInDays: 7
EOF

# Update application.properties for Beanstalk
cat > src/main/resources/application-production.properties << EOF
# Server configuration for Elastic Beanstalk
server.port=5000

# Database configuration (using RDS MySQL)
spring.datasource.url=jdbc:mysql://\${RDS_HOSTNAME:localhost}:\${RDS_PORT:3306}/\${RDS_DB_NAME:productdb}
spring.datasource.username=\${RDS_USERNAME:admin}
spring.datasource.password=\${RDS_PASSWORD:password}
spring.datasource.driver-class-name=com.mysql.cj.jdbc.Driver

# JPA configuration
spring.jpa.database-platform=org.hibernate.dialect.MySQL8Dialect
spring.jpa.hibernate.ddl-auto=update
spring.jpa.show-sql=false

# Actuator for health checks
management.endpoints.web.exposure.include=health,info
management.endpoint.health.show-details=always

# Logging
logging.level.org.springframework=INFO
logging.level.com.example=INFO
logging.file.name=/var/log/java21-app.log
EOF

echo "📦 Step 2: Building application..."
./mvnw clean package -DskipTests

if [ $? -ne 0 ]; then
    echo "❌ Build failed!"
    exit 1
fi

echo "✅ Application built successfully!"

echo "🚀 Step 3: Initializing Elastic Beanstalk application..."
# Initialize EB application
eb init $APP_NAME --platform "$PLATFORM" --region $REGION

# Create Procfile for Java application
cat > Procfile << EOF
web: java -Dserver.port=5000 -jar target/java21-app-0.0.1-SNAPSHOT.jar
EOF

echo "🌍 Step 4: Creating Elastic Beanstalk environment..."
# Create environment with configuration
eb create $ENV_NAME \
    --instance-type $INSTANCE_TYPE \
    --platform "$PLATFORM" \
    --region $REGION \
    --envvars SPRING_PROFILES_ACTIVE=production

if [ $? -eq 0 ]; then
    echo "✅ Environment created successfully!"
else
    echo "❌ Failed to create environment"
    exit 1
fi

echo "📤 Step 5: Deploying application..."
eb deploy $ENV_NAME

if [ $? -eq 0 ]; then
    echo "✅ Deployment successful!"
else
    echo "❌ Deployment failed"
    exit 1
fi

# Get environment URL
ENV_URL=$(eb status $ENV_NAME | grep "CNAME" | awk '{print $2}')

echo "🗄️  Step 6: Setting up RDS database (optional)..."
cat << EOF

To add a managed database (recommended for production):

1. Create RDS MySQL instance:
   aws rds create-db-instance \\
     --db-instance-identifier java21-db \\
     --db-instance-class db.t3.micro \\
     --engine mysql \\
     --master-username admin \\
     --master-user-password YourSecurePassword123 \\
     --allocated-storage 20 \\
     --region $REGION

2. Update environment variables:
   eb setenv RDS_HOSTNAME=java21-db.xxxxx.$REGION.rds.amazonaws.com \\
            RDS_PORT=3306 \\
            RDS_DB_NAME=productdb \\
            RDS_USERNAME=admin \\
            RDS_PASSWORD=YourSecurePassword123

3. Redeploy:
   eb deploy $ENV_NAME

EOF

echo "✅ Elastic Beanstalk deployment completed!"
echo ""
echo "📊 Deployment Summary:"
echo "   Application: $APP_NAME"
echo "   Environment: $ENV_NAME"
echo "   Platform: $PLATFORM"
echo "   Instance Type: $INSTANCE_TYPE"
echo "   Expected Cost: ~$40-55/month"
echo ""
echo "🌐 Your application is available at:"
echo "   http://$ENV_URL"
echo ""
echo "🔍 Useful EB CLI commands:"
echo "   eb status $ENV_NAME          # Check environment status"
echo "   eb logs $ENV_NAME            # View application logs"
echo "   eb ssh $ENV_NAME             # SSH into instance"
echo "   eb terminate $ENV_NAME       # Terminate environment"
echo ""
echo "💰 Cost Breakdown:"
echo "   • EC2 Instance (t3.small): ~$19/month"
echo "   • Application Load Balancer: ~$16/month"
echo "   • EBS Storage (20GB): ~$2/month"
echo "   • CloudWatch Logs: ~$3/month"
echo "   • Data Transfer: Variable"
echo ""
echo "🎯 Benefits:"
echo "   • Easy deployment and management"
echo "   • Auto-scaling capabilities"
echo "   • Health monitoring"
echo "   • Rolling deployments"
echo "   • Integration with other AWS services"

echo "🎉 Deployment completed! Your Java 21 application is now running on Elastic Beanstalk."
