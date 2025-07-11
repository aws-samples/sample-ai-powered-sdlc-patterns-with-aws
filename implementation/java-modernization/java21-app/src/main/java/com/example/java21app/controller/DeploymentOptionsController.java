package com.example.java21app.controller;

import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;

import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Controller for the AWS Deployment Options page.
 * Displays various AWS deployment options with pricing and recommendations.
 */
@Controller
public class DeploymentOptionsController {

    @GetMapping("/deployment-options")
    public String deploymentOptions(Model model) {
        // Add page metadata
        model.addAttribute("pageTitle", "AWS Deployment Options");
        model.addAttribute("pageDescription", "Choose the best AWS deployment option for your Java 21 service");
        
        // Deployment options data
        List<Map<String, Object>> deploymentOptions = Arrays.asList(
            createDeploymentOption(
                "AWS App Runner",
                "fas fa-rocket",
                "$25-51",
                "medium",
                "Low",
                "5 min",
                "Fully managed container service with auto-scaling",
                Arrays.asList(
                    "Fully managed container service",
                    "Auto-scaling (0-25 instances)",
                    "Built-in load balancing",
                    "HTTPS by default",
                    "Direct GitHub deployment"
                ),
                Arrays.asList("Limited customization"),
                "Quick demos, POCs, simple web apps",
                true,
                "app-runner-deploy.sh"
            ),
            createDeploymentOption(
                "ECS Fargate",
                "fab fa-docker",
                "$47-65",
                "medium",
                "Medium",
                "15 min",
                "Serverless containers with full orchestration control",
                Arrays.asList(
                    "Serverless containers",
                    "Full container control",
                    "Auto-scaling capabilities",
                    "Service discovery",
                    "Blue/green deployments"
                ),
                Arrays.asList("Container expertise needed"),
                "Production workloads, container-based apps",
                false,
                "ecs-fargate-deploy.sh"
            ),
            createDeploymentOption(
                "AWS Lambda",
                "fas fa-bolt",
                "$2-10",
                "low",
                "Medium",
                "10 min",
                "Serverless compute with pay-per-request pricing",
                Arrays.asList(
                    "Pay per request",
                    "Automatic scaling",
                    "No server management",
                    "Event-driven architecture",
                    "First 1M requests free"
                ),
                Arrays.asList("Cold start latency", "15-minute timeout limit"),
                "Variable traffic, event-driven apps",
                false,
                "lambda-deploy.sh"
            ),
            createDeploymentOption(
                "Amazon EC2",
                "fas fa-server",
                "$25-50",
                "medium",
                "High",
                "20 min",
                "Traditional virtual machines with full OS control",
                Arrays.asList(
                    "Full OS control",
                    "Custom configurations",
                    "Reserved instance savings",
                    "Multiple deployment options"
                ),
                Arrays.asList("Infrastructure management", "Security patching required"),
                "Custom requirements, full control needed",
                false,
                "ec2-deploy.sh"
            ),
            createDeploymentOption(
                "Elastic Beanstalk",
                "fas fa-seedling",
                "$40-55",
                "medium",
                "Low",
                "10 min",
                "Platform-as-a-Service with easy deployment",
                Arrays.asList(
                    "Easy deployment",
                    "Auto-scaling",
                    "Health monitoring",
                    "Rolling deployments",
                    "Multiple environments"
                ),
                Arrays.asList("Platform limitations"),
                "Traditional apps, easy management",
                false,
                "elastic-beanstalk-deploy.sh"
            ),
            createDeploymentOption(
                "Amazon EKS",
                "fas fa-dharmachakra",
                "$160-200",
                "high",
                "High",
                "30 min",
                "Managed Kubernetes for advanced orchestration",
                Arrays.asList(
                    "Kubernetes orchestration",
                    "Advanced scaling policies",
                    "Service mesh integration",
                    "Multi-AZ deployment"
                ),
                Arrays.asList("High complexity", "Kubernetes expertise needed"),
                "Enterprise, microservices, complex apps",
                false,
                "eks-deploy.sh"
            )
        );
        
        model.addAttribute("deploymentOptions", deploymentOptions);
        
        // Database options
        List<Map<String, Object>> databaseOptions = Arrays.asList(
            createDatabaseOption("H2 (Current)", "In-Memory", "Embedded", "$0", "low", "Development, demos"),
            createDatabaseOption("RDS PostgreSQL", "Relational", "db.t3.micro", "$13.50", "medium", "Production apps"),
            createDatabaseOption("RDS MySQL", "Relational", "db.t3.micro", "$13.50", "medium", "Traditional apps"),
            createDatabaseOption("Aurora Serverless v2", "Serverless SQL", "0.5-1 ACU", "$43.80", "medium", "Variable workloads"),
            createDatabaseOption("DynamoDB", "NoSQL", "On-Demand", "$1.56", "low", "Serverless apps")
        );
        
        model.addAttribute("databaseOptions", databaseOptions);
        
        // Recommendations by use case
        List<Map<String, Object>> recommendations = Arrays.asList(
            createRecommendation("Quick Demo/POC", "AWS App Runner", "~$25/month", 
                "Fastest deployment, minimal configuration, perfect for demonstrations"),
            createRecommendation("Production Application", "ECS Fargate + RDS", "~$75/month", 
                "Scalable, managed, production-ready with managed database"),
            createRecommendation("Cost-Optimized", "Lambda + DynamoDB", "~$5/month", 
                "Pay per use, serverless, great for variable traffic patterns"),
            createRecommendation("Full Control", "EC2 + RDS", "~$45/month", 
                "Complete infrastructure control, custom configurations"),
            createRecommendation("Enterprise Scale", "EKS + Aurora", "~$250/month", 
                "Advanced orchestration, high availability, microservices")
        );
        
        model.addAttribute("recommendations", recommendations);
        
        return "deployment-options";
    }
    
    private Map<String, Object> createDeploymentOption(String name, String icon, String price, 
            String priceLevel, String complexity, String setupTime, String description,
            List<String> pros, List<String> cons, String bestFor, boolean recommended, String script) {
        Map<String, Object> option = new HashMap<>();
        option.put("name", name);
        option.put("icon", icon);
        option.put("price", price);
        option.put("priceLevel", priceLevel);
        option.put("complexity", complexity);
        option.put("setupTime", setupTime);
        option.put("description", description);
        option.put("pros", pros);
        option.put("cons", cons);
        option.put("bestFor", bestFor);
        option.put("recommended", recommended);
        option.put("script", script);
        return option;
    }
    
    private Map<String, Object> createDatabaseOption(String name, String type, String instance, 
            String cost, String costLevel, String bestFor) {
        Map<String, Object> option = new HashMap<>();
        option.put("name", name);
        option.put("type", type);
        option.put("instance", instance);
        option.put("cost", cost);
        option.put("costLevel", costLevel);
        option.put("bestFor", bestFor);
        return option;
    }
    
    private Map<String, Object> createRecommendation(String useCase, String service, String cost, String reason) {
        Map<String, Object> recommendation = new HashMap<>();
        recommendation.put("useCase", useCase);
        recommendation.put("service", service);
        recommendation.put("cost", cost);
        recommendation.put("reason", reason);
        return recommendation;
    }
}
