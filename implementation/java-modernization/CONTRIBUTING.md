# Contributing to Java Modernization with Amazon Q Developer

Thank you for your interest in contributing to this Java modernization demonstration project! This guide will help you get started with contributing effectively.

## 🎯 Project Overview

This project demonstrates AI-powered Java modernization using Amazon Q Developer, showcasing the transformation from Java 8 through Java 17 to Java 21. We welcome contributions that enhance the demonstration, improve documentation, or add new modernization examples.

## 🤝 How to Contribute

### Types of Contributions

We welcome several types of contributions:

- **Code Examples**: New Java modernization patterns
- **Documentation**: Improvements to README files, guides, and tutorials
- **Testing**: Additional test cases and testing strategies
- **Deployment**: New AWS deployment configurations
- **Performance**: Benchmarking and optimization examples
- **Security**: Security enhancements and best practices

### Getting Started

1. **Fork the Repository**
   ```bash
   # Fork the repo on GitHub, then clone your fork
   git clone https://github.com/your-username/java-modernization.git
   cd java-modernization
   ```

2. **Set Up Development Environment**
   ```bash
   # Ensure you have the required tools
   java -version  # Should be Java 21+
   mvn -version   # Should be Maven 3.8+
   
   # Run the cleanup script to ensure clean state
   ./cleanup.sh
   ```

3. **Create a Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

## 🛠️ Development Guidelines

### Code Standards

#### Java Code Style
- Follow standard Java naming conventions
- Use modern Java features appropriately for each version
- Include comprehensive JavaDoc for public APIs
- Maintain consistent formatting (use your IDE's formatter)

#### Example Code Structure
```java
/**
 * Demonstrates Java 21 pattern matching with sealed classes.
 * 
 * @author Your Name
 * @since 1.0
 */
public class ModernPatternExample {
    
    /**
     * Processes different product types using pattern matching.
     * 
     * @param product the product to process
     * @return formatted description
     */
    public String processProduct(Product product) {
        return switch (product) {
            case ElectronicsProduct(var name, var price) when price.compareTo(BigDecimal.valueOf(1000)) > 0 ->
                "Premium electronics: " + name + " ($" + price + ")";
            case ElectronicsProduct(var name, var price) ->
                "Standard electronics: " + name + " ($" + price + ")";
            case ClothingProduct(var name, var size, var color) ->
                "Clothing: " + name + " (Size: " + size + ", Color: " + color + ")";
            default -> "Unknown product type";
        };
    }
}
```

### Testing Requirements

All contributions must include appropriate tests:

#### Unit Tests
```java
@Test
@DisplayName("Should process electronics product with pattern matching")
void shouldProcessElectronicsProduct() {
    // Given
    var product = new ElectronicsProduct("Laptop", new BigDecimal("1500"));
    var processor = new ModernPatternExample();
    
    // When
    var result = processor.processProduct(product);
    
    // Then
    assertThat(result).contains("Premium electronics");
    assertThat(result).contains("Laptop");
}
```

#### BDD Tests (when applicable)
```gherkin
Feature: Modern Java Pattern Matching
  
  Scenario: Process premium electronics product
    Given I have an electronics product with price over $1000
    When I process the product using pattern matching
    Then the result should indicate it's a premium product
    And the result should include the product name and price
```

### Documentation Standards

#### README Updates
- Use clear, concise language
- Include code examples with explanations
- Add performance metrics when relevant
- Update table of contents if needed

#### AI Prompt Documentation
When adding new AI-generated code, include the prompts used:

```markdown
### AI Development Prompt Used

```
Create a Java 21 example demonstrating sealed classes with pattern matching:

1. Define a sealed Product interface with specific implementations
2. Use pattern matching in switch expressions
3. Include guard conditions for complex logic
4. Add comprehensive JavaDoc documentation
5. Include unit tests with JUnit 5
6. Demonstrate performance benefits over traditional approaches

Focus on practical, real-world usage patterns.
```
```

## 🧪 Testing Your Changes

### Running Tests
```bash
# Run all tests for all Java versions
./mvnw test

# Run tests for specific application
cd java21-app && ./mvnw test

# Run with coverage
./mvnw test jacoco:report

# Run BDD tests
./mvnw test -Dtest=CucumberRunnerTest
```

### Manual Testing
```bash
# Start all applications
./start-all-java-apps.sh

# Test individual applications
cd java8-app && ./mvnw spring-boot:run   # http://localhost:8080
cd java17-app && ./mvnw spring-boot:run  # http://localhost:8081
cd java21-app && ./mvnw spring-boot:run  # http://localhost:8082
```

## 📝 Commit Guidelines

### Commit Message Format
```
<type>(<scope>): <subject>

<body>

<footer>
```

#### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

#### Examples
```bash
feat(java21): add virtual threads example with performance metrics

- Implement virtual thread pool for concurrent processing
- Add performance comparison with traditional threads
- Include comprehensive benchmarking tests
- Update documentation with usage examples

Closes #123
```

```bash
docs(readme): update Java 17 modernization prompts

- Correct grammar and spelling in AI prompts
- Add missing code examples for lambda expressions
- Include performance improvement metrics
- Fix formatting issues in code blocks
```

## 🔍 Code Review Process

### Before Submitting
1. **Self-Review**: Review your own changes thoroughly
2. **Test Coverage**: Ensure adequate test coverage
3. **Documentation**: Update relevant documentation
4. **Clean History**: Squash commits if necessary
5. **Rebase**: Rebase on latest main branch

### Pull Request Template
```markdown
## Description
Brief description of changes and motivation.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Code refactoring

## Java Version Impact
- [ ] Java 8 application
- [ ] Java 17 application  
- [ ] Java 21 application
- [ ] All versions

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] BDD tests added/updated
- [ ] Manual testing completed

## AI Prompts Used
Include any Amazon Q Developer prompts used for code generation.

## Performance Impact
Describe any performance implications (positive or negative).

## Documentation
- [ ] README updated
- [ ] Code comments added
- [ ] API documentation updated
```

## 🚀 Deployment Testing

### AWS Deployment Scripts
If your changes affect deployment:

```bash
# Test deployment scripts
cd deployment-scripts

# Test App Runner deployment
./app-runner-deploy.sh --dry-run

# Test ECS Fargate deployment
./ecs-fargate-deploy.sh --validate

# Test Lambda deployment
./lambda-deploy.sh --check-config
```

## 📊 Performance Benchmarking

### Adding Performance Tests
```java
@Test
@DisplayName("Should demonstrate performance improvement over Java 8")
void shouldShowPerformanceImprovement() {
    var products = generateTestProducts(10000);
    
    // Java 8 approach
    var start = System.nanoTime();
    var java8Result = processWithJava8Patterns(products);
    var java8Time = System.nanoTime() - start;
    
    // Modern approach
    start = System.nanoTime();
    var modernResult = processWithModernPatterns(products);
    var modernTime = System.nanoTime() - start;
    
    // Verify results are equivalent
    assertThat(modernResult).isEqualTo(java8Result);
    
    // Verify performance improvement
    assertThat(modernTime).isLessThan(java8Time);
    
    // Log performance metrics
    log.info("Java 8 time: {}ms, Modern time: {}ms, Improvement: {}%",
        java8Time / 1_000_000,
        modernTime / 1_000_000,
        ((java8Time - modernTime) * 100.0) / java8Time);
}
```

## 🛡️ Security Considerations

### Security Checklist
- [ ] No hardcoded credentials or secrets
- [ ] Input validation for all user inputs
- [ ] SQL injection prevention
- [ ] XSS protection in web interfaces
- [ ] Dependency vulnerability scanning
- [ ] OWASP compliance verification

### Security Testing
```bash
# Run security scans
./mvnw org.owasp:dependency-check-maven:check

# Run with security profile
./mvnw test -Psecurity
```

## 🤖 AI-Powered Development

### Using Amazon Q Developer
When contributing AI-generated code:

1. **Document Prompts**: Include the exact prompts used
2. **Review Output**: Carefully review all generated code
3. **Test Thoroughly**: Ensure generated code works correctly
4. **Optimize**: Refine generated code for best practices
5. **Explain**: Add comments explaining complex AI-generated logic

### Best Practices for AI Prompts
- Be specific about requirements
- Include context about the existing codebase
- Specify coding standards and patterns
- Request comprehensive testing
- Ask for documentation and comments

## 📞 Getting Help

### Communication Channels
- **GitHub Issues**: For bug reports and feature requests
- **GitHub Discussions**: For questions and general discussion
- **Pull Request Comments**: For code-specific discussions

### Reporting Issues
When reporting issues, include:
- Java version and environment details
- Steps to reproduce the issue
- Expected vs. actual behavior
- Relevant log output
- Screenshots (for UI issues)

## 🎉 Recognition

Contributors will be recognized in:
- Project README acknowledgments
- Release notes for significant contributions
- GitHub contributor statistics

## 📄 License

By contributing to this project, you agree that your contributions will be licensed under the same MIT License that covers the project.

---

**Thank you for contributing to the Java Modernization project! Your contributions help demonstrate the power of AI-assisted development with Amazon Q Developer.**
