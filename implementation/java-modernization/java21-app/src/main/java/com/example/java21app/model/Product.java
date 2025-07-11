package com.example.java21app.model;

import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import java.time.LocalDateTime;

/**
 * Product entity using Jakarta Persistence API.
 * Modernized with Java 21 features.
 */
@Entity
public class Product {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    private String name;
    private String description;
    private Double price;
    private LocalDateTime createdDate;
    private Boolean available;

    // Default constructor required by JPA
    public Product() {
    }

    public Product(String name, String description, Double price, Boolean available) {
        this.name = name;
        this.description = description;
        this.price = price;
        this.createdDate = LocalDateTime.now();
        this.available = available;
    }

    // Getters and setters
    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public String getDescription() {
        return description;
    }

    public void setDescription(String description) {
        this.description = description;
    }

    public Double getPrice() {
        return price;
    }

    public void setPrice(Double price) {
        this.price = price;
    }

    public LocalDateTime getCreatedDate() {
        return createdDate;
    }

    public void setCreatedDate(LocalDateTime createdDate) {
        this.createdDate = createdDate;
    }

    public Boolean getAvailable() {
        return available;
    }

    public void setAvailable(Boolean available) {
        this.available = available;
    }

    // Using Java 21 text blocks for toString method
    @Override
    public String toString() {
        return """
               Product {
                 id: %d,
                 name: '%s',
                 description: '%s',
                 price: %.2f,
                 createdDate: %s,
                 available: %b
               }
               """.formatted(id, name, description, price, createdDate, available);
    }
}
