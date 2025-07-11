package com.example.java8app.config;

import com.example.java8app.model.Product;
import com.example.java8app.repository.ProductRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

@Component
public class DataInitializer implements CommandLineRunner {

    @Autowired
    private ProductRepository productRepository;

    @Override
    public void run(String... args) throws Exception {
        // Clear any existing data
        productRepository.deleteAll();
        
        // Add sample products
        productRepository.save(new Product("Laptop", "High-performance laptop with 16GB RAM", 1299.99, true));
        productRepository.save(new Product("Smartphone", "Latest model with 128GB storage", 899.99, true));
        productRepository.save(new Product("Tablet", "10-inch screen with 64GB storage", 499.99, true));
        productRepository.save(new Product("Headphones", "Noise-cancelling wireless headphones", 249.99, true));
        productRepository.save(new Product("Monitor", "27-inch 4K monitor", 349.99, false));
        productRepository.save(new Product("Keyboard", "Mechanical gaming keyboard", 129.99, true));
        productRepository.save(new Product("Mouse", "Wireless ergonomic mouse", 59.99, true));
        productRepository.save(new Product("Printer", "Color laser printer", 299.99, false));
        productRepository.save(new Product("External Hard Drive", "2TB portable hard drive", 89.99, true));
        productRepository.save(new Product("Webcam", "HD webcam with microphone", 79.99, false));
        
        System.out.println("Sample data initialized successfully!");
    }
}
