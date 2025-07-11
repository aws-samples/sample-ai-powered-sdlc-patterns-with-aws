package com.example.java8app.service;

import com.example.java8app.model.Product;
import com.example.java8app.repository.ProductRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;

@Service
public class ProductService {

    @Autowired
    private ProductRepository productRepository;

    public List<Product> getAllProducts() {
        List<Product> products = productRepository.findAll();
        return products;
    }

    public Product getProductById(Long id) {
        return productRepository.findById(id).orElse(null);
    }

    public Product createProduct(Product product) {
        return productRepository.save(product);
    }

    public Product updateProduct(Long id, Product productDetails) {
        Product product = productRepository.findById(id).orElse(null);
        if (product != null) {
            product.setName(productDetails.getName());
            product.setDescription(productDetails.getDescription());
            product.setPrice(productDetails.getPrice());
            product.setAvailable(productDetails.getAvailable());
            return productRepository.save(product);
        }
        return null;
    }

    public void deleteProduct(Long id) {
        productRepository.deleteById(id);
    }

    // Java 8 style method using anonymous inner class
    public List<Product> getSortedProductsByPrice() {
        List<Product> products = new ArrayList<>(productRepository.findAll());
        Collections.sort(products, new Comparator<Product>() {
            @Override
            public int compare(Product p1, Product p2) {
                return p1.getPrice().compareTo(p2.getPrice());
            }
        });
        return products;
    }

    // Method using Java 8 lambda expression (to be modernized)
    public List<Product> getAvailableProducts() {
        List<Product> allProducts = productRepository.findAll();
        List<Product> availableProducts = new ArrayList<>();
        
        for (Product product : allProducts) {
            if (product.getAvailable()) {
                availableProducts.add(product);
            }
        }
        
        return availableProducts;
    }

    // Method using old-style exception handling (to be modernized)
    public Double calculateTotalInventoryValue() {
        Double total = 0.0;
        try {
            List<Product> products = productRepository.findAll();
            for (Product product : products) {
                total += product.getPrice();
            }
            return total;
        } catch (Exception e) {
            System.out.println("Error calculating inventory value: " + e.getMessage());
            return 0.0;
        }
    }
}
