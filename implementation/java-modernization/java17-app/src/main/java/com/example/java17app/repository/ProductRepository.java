package com.example.java17app.repository;

import com.example.java17app.model.Product;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface ProductRepository extends JpaRepository<Product, Long> {
    List<Product> findByAvailable(Boolean available);
    List<Product> findByNameContaining(String name);
}
