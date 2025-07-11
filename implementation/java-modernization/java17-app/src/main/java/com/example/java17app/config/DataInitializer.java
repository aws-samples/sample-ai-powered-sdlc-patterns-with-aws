package com.example.java17app.config;

import com.example.java17app.model.Product;
import com.example.java17app.repository.ProductRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

import java.util.List;

@Component
public class DataInitializer implements CommandLineRunner {

    private static final Logger logger = LoggerFactory.getLogger(DataInitializer.class);

    @Autowired
    private ProductRepository productRepository;

    @Override
    public void run(String... args) {
        // Clear any existing data
        productRepository.deleteAll();
        
        // Add sample products using Java 17 features
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
        
        productRepository.saveAll(products);
        
        logger.info("Sample data initialized successfully with {} products!", products.size());
    }
}
