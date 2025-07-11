package com.example.java21app.dto;

import com.example.java21app.model.Product;
import java.time.LocalDateTime;

/**
 * Product DTO using Java 21 record feature.
 * Records provide a compact syntax for declaring classes that are transparent holders for shallowly immutable data.
 */
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
        if (price == null || price < 0) {
            throw new IllegalArgumentException("Price cannot be negative");
        }
    }
    
    // Static factory method using pattern matching
    public static ProductDTO fromProduct(Object obj) {
        if (obj instanceof Product p) {
            return new ProductDTO(
                p.getId(), 
                p.getName(), 
                p.getDescription(), 
                p.getPrice(), 
                p.getCreatedDate(), 
                p.getAvailable()
            );
        } else if (obj == null) {
            throw new IllegalArgumentException("Product cannot be null");
        } else {
            throw new IllegalArgumentException("Not a valid product object");
        }
    }
    
    // Convert back to entity
    public Product toEntity() {
        Product product = new Product();
        product.setId(id);
        product.setName(name);
        product.setDescription(description);
        product.setPrice(price);
        product.setCreatedDate(createdDate);
        product.setAvailable(available);
        return product;
    }
}
