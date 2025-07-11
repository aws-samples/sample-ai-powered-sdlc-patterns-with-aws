package com.example.java21app.repository;

import com.example.java21app.model.Product;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

/**
 * Repository interface for Product entity.
 */
@Repository
public interface ProductRepository extends JpaRepository<Product, Long> {
    List<Product> findByAvailable(Boolean available);
    List<Product> findByNameContaining(String name);
}
