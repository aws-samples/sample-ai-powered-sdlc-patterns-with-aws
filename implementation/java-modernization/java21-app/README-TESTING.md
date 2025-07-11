# Java 21 Application Testing Documentation

This document provides information about the testing strategy and tools used for the Java 21 modernized application.

## Table of Contents

1. [Unit Tests](#unit-tests)
2. [Cucumber BDD Tests](#cucumber-bdd-tests)
3. [SonarQube Analysis](#sonarqube-analysis)
4. [OWASP Dependency Check](#owasp-dependency-check)
5. [Running All Tests and Reports](#running-all-tests-and-reports)

## Unit Tests

The application includes comprehensive unit tests for all layers:

- **Service Layer Tests**: Testing business logic in isolation
- **Controller Layer Tests**: Testing API endpoints
- **DTO Tests**: Testing data transfer objects and their validation
- **Repository Tests**: Testing data access

To run unit tests:

```bash
mvn test
```

## Cucumber BDD Tests

Behavior-Driven Development (BDD) tests are implemented using Cucumber. These tests verify the application's behavior from a user's perspective.

Feature files are located in `src/test/resources/features/` and include:

- `product_management.feature`: Tests for CRUD operations on products
- `product_categorization.feature`: Tests for product categorization features

To run Cucumber tests:

```bash
mvn verify -Dcucumber.filter.tags="not @ignore"
```

The Cucumber reports will be generated at `target/cucumber-reports/cucumber-pretty.html`.

## SonarQube Analysis

SonarQube is used for static code analysis to identify code smells, bugs, and security vulnerabilities.

To run SonarQube analysis (requires SonarQube server running):

```bash
mvn sonar:sonar -Dsonar.host.url=http://localhost:9000 -Dsonar.login=admin -Dsonar.password=admin
```

Key metrics tracked:
- Code coverage
- Duplicated code
- Code smells
- Security vulnerabilities
- Technical debt

## OWASP Dependency Check

OWASP Dependency Check is used to identify known vulnerabilities in project dependencies.

To run OWASP Dependency Check:

```bash
mvn org.owasp:dependency-check-maven:check
```

The report will be generated at `target/dependency-check-report.html`.

## Running All Tests and Reports

A convenience script is provided to run all tests and generate all reports:

```bash
./generate-reports.sh
```

This will:
1. Run unit tests and generate JaCoCo coverage report
2. Run Cucumber BDD tests
3. Generate SonarQube report
4. Generate OWASP dependency check report

## Test Coverage Goals

- Unit Test Coverage: >80%
- Feature Coverage: 100% of critical business flows
- Security Vulnerabilities: 0 high or critical issues

## Continuous Integration

These tests are designed to be integrated into a CI/CD pipeline. The Maven configuration includes all necessary plugins for test execution and reporting.
