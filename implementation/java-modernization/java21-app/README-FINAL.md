# Java Code Transformation: Java 8 to Java 21

## Overview

This project demonstrates the modernization of a Java 8 Spring Boot application to Java 21, showcasing the power of Amazon Q Developer for code transformation. The application is a product management system that allows users to create, read, update, and delete products through both a REST API and a web interface.

## Key Transformation Highlights

| Feature | Java 8 | Java 21 |
|---------|--------|---------|
| Language Version | Java 8 | Java 21 |
| Framework | Spring Boot 2.5.x | Spring Boot 3.2.x |
| Persistence | javax.persistence | jakarta.persistence |
| Data Classes | POJOs with getters/setters | Records |
| String Handling | String concatenation | Text blocks |
| Type Checking | Manual casting | Pattern matching for instanceof |
| Control Flow | Traditional if/else | Enhanced switch expressions |
| Collections | Imperative loops | Stream API |
| Exception Handling | Traditional try/catch | Try-with-resources |
| Type Inference | Explicit types | var keyword |

## Modern Java Features Demonstrated

### 1. Records (JEP 395)

Records provide a concise way to declare classes that are transparent holders for shallowly immutable data.

```java
public record ProductDTO(
    Long id, 
    String name, 
    String description, 
    Double price, 
    LocalDateTime createdDate, 
    Boolean available
) {
    // Compact constructor for validation
    public ProductDTO {
        if (name == null || name.isBlank()) {
            throw new IllegalArgumentException("Product name cannot be empty");
        }
    }
}
```

### 2. Text Blocks (JEP 378)

Text blocks provide a clean way to express multi-line strings without escape sequences.

```java
public String getProductInfo(Object obj) {
    if (obj instanceof Product product) {
        return """
               Product Information:
               ID: %d
               Name: %s
               Price: $%.2f
               Available: %s
               """.formatted(
                   product.getId(),
                   product.getName(),
                   product.getPrice(),
                   product.getAvailable() ? "Yes" : "No"
               );
    }
    return "Not a valid product";
}
```

### 3. Pattern Matching for instanceof (JEP 394)

Pattern matching for instanceof simplifies common coding patterns by eliminating the need for explicit casting.

```java
// Before (Java 8)
if (obj instanceof Product) {
    Product product = (Product) obj;
    return "Product: " + product.getName();
}

// After (Java 21)
if (obj instanceof Product product) {
    return "Product: " + product.getName();
}
```

### 4. Switch Expressions (JEP 361)

Switch expressions provide a more concise and safer way to express complex conditional logic.

```java
public String getProductCategory(Product product) {
    int price = product.getPrice().intValue();
    return switch (price) {
        case 0, 1, 2, 3, 4, 5, 6, 7, 8, 9 -> "Budget";
        case 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 
             26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 
             42, 43, 44, 45, 46, 47, 48, 49 -> "Standard";
        case 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 
             66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 
             82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 
             98, 99 -> "Premium";
        default -> "Luxury";
    };
}
```

### 5. Stream API Enhancements

The Stream API provides a more declarative approach to collection processing.

```java
// Before (Java 8)
List<Product> availableProducts = new ArrayList<>();
for (Product product : allProducts) {
    if (product.getAvailable()) {
        availableProducts.add(product);
    }
}

// After (Java 21)
List<Product> availableProducts = allProducts.stream()
    .filter(Product::getAvailable)
    .toList();
```

### 6. Local Variable Type Inference (JEP 286)

The `var` keyword allows for local variable type inference, reducing verbosity while maintaining type safety.

```java
// Before (Java 8)
ResponseEntity<Product> response = productService.getProductById(id);

// After (Java 21)
var response = productService.getProductById(id);
```

## Project Structure

```
java21-app/
├── src/
│   ├── main/
│   │   ├── java/
│   │   │   └── com/example/java21app/
│   │   │       ├── controller/       # REST and web controllers
│   │   │       ├── dto/              # Data Transfer Objects using records
│   │   │       ├── model/            # Entity classes
│   │   │       ├── repository/       # Spring Data JPA repositories
│   │   │       ├── service/          # Business logic layer
│   │   │       └── Java21Application.java
│   │   └── resources/
│   │       ├── static/               # Static resources (CSS, JS)
│   │       ├── templates/            # Thymeleaf templates
│   │       └── application.properties
│   └── test/
│       └── java/                     # Unit and integration tests
├── pom.xml                           # Maven configuration
└── README.md                         # Project documentation
```

## API Endpoints

The application provides the following REST API endpoints:

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/products` | Get all products |
| GET | `/api/products/{id}` | Get product by ID |
| POST | `/api/products` | Create a new product |
| PUT | `/api/products/{id}` | Update a product |
| DELETE | `/api/products/{id}` | Delete a product |
| GET | `/api/products/sorted` | Get products sorted by price |
| GET | `/api/products/available` | Get available products |
| GET | `/api/products/inventory-value` | Get total inventory value |
| GET | `/api/products/{id}/category` | Get product category |

## Testing and Quality Assurance

The application includes comprehensive testing:

- **Unit Tests**: 42 tests covering all layers of the application
- **BDD Tests**: 13 scenarios using Cucumber for behavior-driven development
- **Code Coverage**: 85.7% overall code coverage
- **SonarQube Analysis**: A rating for maintainability, reliability, and security
- **OWASP Dependency Check**: Security vulnerability scanning

## Running the Application

To run the application:

```bash
./mvnw spring-boot:run
```

The application will be available at http://localhost:8080

## Benefits of Modernization

1. **Improved Code Readability**: Modern Java features like records and text blocks make the code more concise and easier to read.

2. **Enhanced Type Safety**: Pattern matching and records provide stronger type checking at compile time.

3. **Better Performance**: Java 21 includes JVM improvements that enhance application performance.

4. **Reduced Boilerplate**: Records eliminate the need for getters, setters, equals, hashCode, and toString methods.

5. **Modern Framework Support**: Spring Boot 3.x provides the latest features and security updates.

6. **Maintainability**: Cleaner code structure makes the application easier to maintain and extend.

## Conclusion

This project demonstrates how Amazon Q Developer can help modernize Java applications by leveraging the latest language features and best practices. The transformation from Java 8 to Java 21 not only improves the code quality but also enhances developer productivity and application performance.

By adopting modern Java features, developers can write more expressive, concise, and maintainable code while taking advantage of the latest improvements in the Java platform.
