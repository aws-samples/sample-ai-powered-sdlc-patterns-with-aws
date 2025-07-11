#!/bin/bash

# Run unit tests and generate JaCoCo coverage report
echo "Running unit tests and generating coverage report..."
mvn clean test jacoco:report

# Run Cucumber BDD tests
echo "Running Cucumber BDD tests..."
mvn verify -Dcucumber.filter.tags="not @ignore"

# Generate SonarQube report
echo "Generating SonarQube report..."
mvn sonar:sonar -Dsonar.host.url=http://localhost:9000 -Dsonar.login=admin -Dsonar.password=admin

# Generate OWASP dependency check report
echo "Generating OWASP dependency check report..."
mvn org.owasp:dependency-check-maven:check

echo "All reports generated successfully!"
echo "JaCoCo coverage report: target/site/jacoco/index.html"
echo "Cucumber BDD report: target/cucumber-reports/cucumber-pretty.html"
echo "OWASP dependency check report: target/dependency-check-report.html"
