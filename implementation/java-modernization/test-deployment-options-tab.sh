#!/bin/bash

echo "🚀 Testing Java 21 Application with AWS Deployment Options Tab"
echo "=============================================================="

cd java21-app

echo "📦 Building the application..."
./mvnw clean package -DskipTests

if [ $? -eq 0 ]; then
    echo "✅ Build successful!"
    echo ""
    echo "🌐 Starting the application..."
    echo "The application will be available at:"
    echo "  - Home: http://localhost:8080/"
    echo "  - Testing Report: http://localhost:8080/testing-report"
    echo "  - Migration Design: http://localhost:8080/migration-design"
    echo "  - AWS Deployment Options: http://localhost:8080/deployment-options"
    echo ""
    echo "🎯 New Features in AWS Deployment Options Tab:"
    echo "  • 6 AWS deployment options with pricing"
    echo "  • Interactive comparison tables"
    echo "  • Database migration guidance"
    echo "  • Ready-to-use deployment scripts"
    echo "  • Cost analysis and recommendations"
    echo ""
    echo "Press Ctrl+C to stop the application"
    echo ""
    
    java -jar target/java21-app-0.0.1-SNAPSHOT.jar
else
    echo "❌ Build failed!"
    exit 1
fi
