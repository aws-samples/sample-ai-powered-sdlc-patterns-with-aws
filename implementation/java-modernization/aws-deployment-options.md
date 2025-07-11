# AWS Deployment Options for Java 21 Service

## Application Profile
- **Technology**: Spring Boot 3.2.3 with Java 21
- **Database**: H2 (in-memory) - can be migrated to RDS
- **Port**: 8082
- **Type**: Web application with REST APIs
- **Size**: Small to medium workload

---

## 1. 🚀 AWS App Runner (Recommended for Simplicity)

### Overview
Fully managed container service that automatically builds and deploys your application from source code.

### Features
- ✅ Automatic scaling (0-25 instances)
- ✅ Built-in load balancing
- ✅ HTTPS by default
- ✅ No infrastructure management
- ✅ Direct deployment from GitHub/ECR

### Configuration
```yaml
# apprunner.yaml
version: 1.0
runtime: java21
build:
  commands:
    build:
      - echo "Building Java 21 application"
      - ./mvnw clean package -DskipTests
run:
  runtime-version: 21
  command: java -jar target/java21-app-0.0.1-SNAPSHOT.jar
  network:
    port: 8082
    env: PORT
  env:
    - name: SPRING_PROFILES_ACTIVE
      value: production
```

### Pricing (US East - N. Virginia)
| Component | Specification | Monthly Cost |
|-----------|---------------|--------------|
| **Basic Plan** | 0.25 vCPU, 0.5 GB RAM | $7.00/month |
| **Standard Plan** | 1 vCPU, 2 GB RAM | $25.50/month |
| **High Performance** | 2 vCPU, 4 GB RAM | $51.00/month |
| **Data Transfer** | First 100 GB free | $0.09/GB after |
| **Build Time** | 100 build minutes/month free | $0.005/minute after |

**Estimated Monthly Cost: $25-51** (for typical usage)

---

## 2. 🐳 Amazon ECS with Fargate (Recommended for Production)

### Overview
Serverless container platform with full control over container orchestration.

### Features
- ✅ Serverless containers
- ✅ Auto-scaling based on metrics
- ✅ Integration with ALB/NLB
- ✅ Service discovery
- ✅ Blue/green deployments

### Configuration
```dockerfile
# Dockerfile
FROM amazoncorretto:21-alpine
COPY target/java21-app-0.0.1-SNAPSHOT.jar app.jar
EXPOSE 8082
ENTRYPOINT ["java", "-jar", "/app.jar"]
```

```yaml
# ecs-task-definition.json
{
  "family": "java21-app",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "java21-app",
      "image": "your-account.dkr.ecr.region.amazonaws.com/java21-app:latest",
      "portMappings": [
        {
          "containerPort": 8082,
          "protocol": "tcp"
        }
      ]
    }
  ]
}
```

### Pricing (US East - N. Virginia)
| Component | Specification | Monthly Cost |
|-----------|---------------|--------------|
| **Fargate vCPU** | 0.5 vCPU × 730 hours | $17.79/month |
| **Fargate Memory** | 1 GB × 730 hours | $3.65/month |
| **Application Load Balancer** | 1 ALB | $16.20/month |
| **ECR Repository** | 0.5 GB storage | $0.05/month |
| **Data Transfer** | 100 GB/month | $9.00/month |

**Estimated Monthly Cost: $47-65** (single instance)

---

## 3. ☁️ AWS Lambda (Serverless)

### Overview
Serverless compute for event-driven applications with cold start considerations.

### Features
- ✅ Pay per request
- ✅ Automatic scaling
- ✅ No server management
- ✅ Integration with API Gateway
- ⚠️ Cold start latency for Java

### Configuration
```java
// LambdaHandler.java
@Component
public class LambdaHandler implements RequestHandler<APIGatewayProxyRequestEvent, APIGatewayProxyResponseEvent> {
    
    @Autowired
    private ProductService productService;
    
    @Override
    public APIGatewayProxyResponseEvent handleRequest(APIGatewayProxyRequestEvent input, Context context) {
        // Handle HTTP requests
        return new APIGatewayProxyResponseEvent()
            .withStatusCode(200)
            .withBody(JsonUtils.toJson(productService.getAllProducts()));
    }
}
```

### Pricing (US East - N. Virginia)
| Component | Specification | Monthly Cost |
|-----------|---------------|--------------|
| **Lambda Requests** | 100,000 requests/month | $0.20/month |
| **Lambda Duration** | 512 MB, 1000ms avg, 100K requests | $0.83/month |
| **API Gateway** | 100,000 API calls | $0.35/month |
| **CloudWatch Logs** | 1 GB logs | $0.50/month |

**Estimated Monthly Cost: $2-10** (low to moderate traffic)

---

## 4. 🖥️ Amazon EC2 (Traditional VMs)

### Overview
Virtual machines with full control over the operating system and runtime environment.

### Features
- ✅ Full control over environment
- ✅ Custom configurations
- ✅ Multiple deployment options
- ✅ Reserved instance savings
- ❌ Infrastructure management required

### Configuration
```bash
#!/bin/bash
# user-data.sh
yum update -y
yum install -y java-21-amazon-corretto
wget https://your-bucket.s3.amazonaws.com/java21-app-0.0.1-SNAPSHOT.jar
java -jar java21-app-0.0.1-SNAPSHOT.jar
```

### Pricing (US East - N. Virginia)
| Instance Type | vCPU | Memory | Storage | Monthly Cost |
|---------------|------|--------|---------|--------------|
| **t3.micro** | 2 | 1 GB | 8 GB EBS | $8.50/month |
| **t3.small** | 2 | 2 GB | 20 GB EBS | $19.00/month |
| **t3.medium** | 2 | 4 GB | 30 GB EBS | $34.00/month |
| **Application Load Balancer** | - | - | - | $16.20/month |

**Estimated Monthly Cost: $25-50** (including ALB)

---

## 5. ⚡ AWS Elastic Beanstalk

### Overview
Platform-as-a-Service that handles deployment, monitoring, and scaling automatically.

### Features
- ✅ Easy deployment
- ✅ Auto-scaling
- ✅ Health monitoring
- ✅ Multiple environment support
- ✅ Rolling deployments

### Configuration
```yaml
# .ebextensions/java.config
option_settings:
  aws:elasticbeanstalk:application:environment:
    SERVER_PORT: 5000
    SPRING_PROFILES_ACTIVE: production
  aws:elasticbeanstalk:container:java:
    JVMOptions: '-Xmx512m -Xms256m'
```

### Pricing (US East - N. Virginia)
| Component | Specification | Monthly Cost |
|-----------|---------------|--------------|
| **EC2 Instance** | t3.small | $19.00/month |
| **Application Load Balancer** | 1 ALB | $16.20/month |
| **EBS Storage** | 20 GB gp3 | $1.60/month |
| **CloudWatch** | Basic monitoring | $3.00/month |

**Estimated Monthly Cost: $40-55**

---

## 6. 🔄 Amazon EKS (Kubernetes)

### Overview
Managed Kubernetes service for containerized applications with advanced orchestration.

### Features
- ✅ Kubernetes orchestration
- ✅ Advanced scaling policies
- ✅ Service mesh integration
- ✅ Multi-AZ deployment
- ❌ Higher complexity

### Configuration
```yaml
# kubernetes-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: java21-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: java21-app
  template:
    metadata:
      labels:
        app: java21-app
    spec:
      containers:
      - name: java21-app
        image: your-account.dkr.ecr.region.amazonaws.com/java21-app:latest
        ports:
        - containerPort: 8082
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
```

### Pricing (US East - N. Virginia)
| Component | Specification | Monthly Cost |
|-----------|---------------|--------------|
| **EKS Cluster** | Control plane | $73.00/month |
| **Worker Nodes** | 2 × t3.medium | $68.00/month |
| **EBS Storage** | 40 GB gp3 | $3.20/month |
| **Load Balancer** | ALB | $16.20/month |

**Estimated Monthly Cost: $160-200**

---

## 7. 🗄️ Database Options

### Amazon RDS (Recommended)
Replace H2 with managed PostgreSQL/MySQL:

| Database | Instance Type | Monthly Cost |
|----------|---------------|--------------|
| **RDS PostgreSQL** | db.t3.micro | $13.50/month |
| **RDS MySQL** | db.t3.micro | $13.50/month |
| **Aurora Serverless v2** | 0.5-1 ACU | $43.80/month |

### Amazon DynamoDB (NoSQL Alternative)
| Component | Usage | Monthly Cost |
|-----------|-------|--------------|
| **On-Demand** | 100K reads, 50K writes | $1.56/month |
| **Provisioned** | 5 RCU, 5 WCU | $2.50/month |

---

## 📊 Cost Comparison Summary

| Deployment Option | Monthly Cost Range | Best For |
|-------------------|-------------------|----------|
| **AWS App Runner** | $25-51 | Simple deployment, low maintenance |
| **ECS Fargate** | $47-65 | Production workloads, container expertise |
| **AWS Lambda** | $2-10 | Event-driven, variable traffic |
| **EC2** | $25-50 | Full control, custom configurations |
| **Elastic Beanstalk** | $40-55 | Traditional deployment, easy management |
| **EKS** | $160-200 | Enterprise, microservices, complex orchestration |

---

## 🎯 Recommendations by Use Case

### 🏃‍♂️ **Quick Demo/POC**
- **Choice**: AWS App Runner
- **Cost**: ~$25/month
- **Why**: Fastest deployment, minimal configuration

### 🏢 **Production Application**
- **Choice**: ECS Fargate + RDS
- **Cost**: ~$75/month
- **Why**: Scalable, managed, production-ready

### 💰 **Cost-Optimized**
- **Choice**: Lambda + DynamoDB
- **Cost**: ~$5/month
- **Why**: Pay per use, serverless

### 🔧 **Full Control**
- **Choice**: EC2 + RDS
- **Cost**: ~$45/month
- **Why**: Complete infrastructure control

### 🚀 **Enterprise Scale**
- **Choice**: EKS + Aurora
- **Cost**: ~$250/month
- **Why**: Advanced orchestration, high availability

---

## 🛠️ Implementation Scripts

I can provide deployment scripts for any of these options. Which deployment method interests you most?

**Note**: All prices are estimates based on US East (N. Virginia) region and may vary based on actual usage patterns, data transfer, and additional services required.

For accurate pricing calculations, I recommend using the [AWS Pricing Calculator](https://calculator.aws) with your specific requirements.
