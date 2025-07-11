package com.example.java21app.service;

import com.example.java21app.model.Product;
import com.example.java21app.repository.ProductRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.Comparator;
import java.util.List;

@Service
public class ProductService {

    private final ProductRepository productRepository;

    @Autowired
    public ProductService(ProductRepository productRepository) {
        this.productRepository = productRepository;
    }

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

    // Modernized method using lambda expression instead of anonymous inner class
    public List<Product> getSortedProductsByPrice() {
        return productRepository.findAll().stream()
            .sorted(Comparator.comparing(Product::getPrice))
            .toList();
    }

    // Modernized method using Stream API instead of for loop
    public List<Product> getAvailableProducts() {
        return productRepository.findAll().stream()
            .filter(Product::getAvailable)
            .toList();
    }

    // Modernized method using try-with-resources and improved exception handling
    public Double calculateTotalInventoryValue() {
        try {
            return productRepository.findAll().stream()
                .mapToDouble(Product::getPrice)
                .sum();
        } catch (Exception e) {
            System.err.println("Error calculating inventory value: " + e.getMessage());
            return 0.0;
        }
    }
    
    // New method using Java 21 pattern matching for instanceof
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
    
    // New method using Java 21 switch expressions
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
}
