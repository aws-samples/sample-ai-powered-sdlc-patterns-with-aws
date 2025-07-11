package com.example.java17app.service;

import com.example.java17app.model.Product;
import com.example.java17app.repository.ProductRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.stream.Collectors;

@Service
public class ProductService {

    private static final Logger logger = LoggerFactory.getLogger(ProductService.class);

    @Autowired
    private ProductRepository productRepository;

    public List<Product> getAllProducts() {
        return productRepository.findAll();
    }

    public Product getProductById(Long id) {
        return productRepository.findById(id).orElse(null);
    }

    public Product createProduct(Product product) {
        return productRepository.save(product);
    }

    public Product updateProduct(Long id, Product productDetails) {
        return productRepository.findById(id)
                .map(product -> {
                    product.setName(productDetails.getName());
                    product.setDescription(productDetails.getDescription());
                    product.setPrice(productDetails.getPrice());
                    product.setAvailable(productDetails.getAvailable());
                    return productRepository.save(product);
                })
                .orElse(null);
    }

    public void deleteProduct(Long id) {
        productRepository.deleteById(id);
    }

    // Modernized with lambda expression
    public List<Product> getSortedProductsByPrice() {
        return productRepository.findAll().stream()
                .sorted((p1, p2) -> p1.getPrice().compareTo(p2.getPrice()))
                .collect(Collectors.toList());
    }

    // Modernized with Stream API
    public List<Product> getAvailableProducts() {
        return productRepository.findAll().stream()
                .filter(Product::getAvailable)
                .collect(Collectors.toList());
    }

    // Modernized with improved exception handling and Stream API
    public Double calculateTotalInventoryValue() {
        try {
            return productRepository.findAll().stream()
                    .mapToDouble(Product::getPrice)
                    .sum();
        } catch (Exception e) {
            logger.error("Error calculating inventory value: {}", e.getMessage(), e);
            return 0.0;
        }
    }
}
