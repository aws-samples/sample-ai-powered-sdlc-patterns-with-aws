package com.example.java21app.config;

import com.example.java21app.model.Product;
import com.example.java21app.repository.ProductRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

import java.util.List;

/**
 * Initializes sample data for the application.
 */
@Component
public class DataInitializer implements CommandLineRunner {

    private final ProductRepository productRepository;

    @Autowired
    public DataInitializer(ProductRepository productRepository) {
        this.productRepository = productRepository;
    }

    @Override
    public void run(String... args) {
        // Using Java 21 text blocks for multiline strings
        System.out.println("""
            ======================================
            Initializing sample product data...
            ======================================
            """);
        
        // Clear any existing data
        productRepository.deleteAll();
        
        // Create sample products - matching the Java 8 application products
        var products = List.of(
            new Product("Laptop", "High-performance laptop with 16GB RAM", 1299.99, true),
            new Product("Smartphone", "Latest model with 128GB storage", 899.99, true),
            new Product("Tablet", "10-inch screen with 64GB storage", 499.99, true),
            new Product("Headphones", "Noise-cancelling wireless headphones", 249.99, true),
            new Product("Monitor", "27-inch 4K monitor", 349.99, false),
            new Product("Keyboard", "Mechanical gaming keyboard", 129.99, true),
            new Product("Mouse", "Wireless ergonomic mouse", 59.99, true),
            new Product("Printer", "Color laser printer", 299.99, false),
            new Product("External Hard Drive", "2TB portable hard drive", 89.99, true),
            new Product("Webcam", "HD webcam with microphone", 79.99, false)
        );
        
        // Save all products
        productRepository.saveAll(products);
        
        System.out.println("""
            ======================================
            Sample data initialization complete!
            ======================================
            """);
    }
}
