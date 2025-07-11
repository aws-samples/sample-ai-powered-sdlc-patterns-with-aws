#!/bin/bash

echo "Starting security remediation for Java 21 application..."
echo "========================================================="

# Clean and build the project with updated dependencies
echo "Building project with updated dependencies..."
./mvnw clean package -DskipTests

# Run Grype scan on the built JAR
echo "Running Grype scan on the built JAR..."
JAR_FILE=$(find target -name "*.jar" | grep -v "original")
grype $JAR_FILE -o json > src/main/resources/static/java21-grype-remediated.json
grype $JAR_FILE > src/main/resources/static/java21-grype-remediated.txt

# Check for critical and high vulnerabilities
echo "Checking for remaining critical and high vulnerabilities..."
CRITICAL_COUNT=$(grep -c "Critical" src/main/resources/static/java21-grype-remediated.txt || echo "0")
HIGH_COUNT=$(grep -c "High" src/main/resources/static/java21-grype-remediated.txt || echo "0")

echo "Scan complete!"
echo "Critical vulnerabilities: $CRITICAL_COUNT"
echo "High vulnerabilities: $HIGH_COUNT"

# Update the testing report with the new results
if [ "$CRITICAL_COUNT" -eq 0 ] && [ "$HIGH_COUNT" -eq 0 ]; then
    echo "All critical and high vulnerabilities have been resolved!"
    
    # Update the security section in the testing report
    sed -i '' 's/<div class="metric-value">2<\/div>/<div class="metric-value">0<\/div>/g' src/main/resources/static/testing-report.html
    sed -i '' 's/<div class="metric-value">6<\/div>/<div class="metric-value">0<\/div>/g' src/main/resources/static/testing-report.html
    sed -i '' 's/class="metric-card failed"/class="metric-card passed"/g' src/main/resources/static/testing-report.html
    sed -i '' 's/<strong>⚠️ Security Alert:<\/strong> Latest Grype scan detected critical and high vulnerabilities that need immediate attention.*/<strong>✅ Security Update:<\/strong> All critical and high vulnerabilities have been resolved by updating dependencies. Only medium and low-risk issues remain./g' src/main/resources/static/testing-report.html
    
    echo "Testing report has been updated to reflect the security improvements."
else
    echo "There are still vulnerabilities that need to be addressed."
    echo "Please check src/main/resources/static/java21-grype-remediated.txt for details."
fi

echo "========================================================="
echo "Security remediation process completed."
