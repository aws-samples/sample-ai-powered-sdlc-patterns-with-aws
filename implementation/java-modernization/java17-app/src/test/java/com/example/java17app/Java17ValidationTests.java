package com.example.java17app;

import com.example.java17app.model.Product;
import com.example.java17app.repository.ProductRepository;
import com.example.java17app.service.ProductService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;

import java.time.LocalDateTime;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
public class Java17ValidationTests {

    @LocalServerPort
    private int port;

    @Autowired
    private TestRestTemplate restTemplate;

    @Autowired
    private ProductService productService;

    @Autowired
    private ProductRepository productRepository;

    @Test
    void contextLoads() {
        // Verify that the application context loads successfully
    }

    @Test
    void testProductCreation() {
        // Create a new product
        Product product = new Product("Test Product", "Test Description", 99.99, true);
        Product savedProduct = productService.createProduct(product);
        
        // Verify that the product was created with the correct properties
        assertThat(savedProduct).isNotNull();
        assertThat(savedProduct.getId()).isNotNull();
        assertThat(savedProduct.getName()).isEqualTo("Test Product");
        assertThat(savedProduct.getDescription()).isEqualTo("Test Description");
        assertThat(savedProduct.getPrice()).isEqualTo(99.99);
        assertThat(savedProduct.getAvailable()).isTrue();
        assertThat(savedProduct.getCreatedDate()).isNotNull();
    }

    @Test
    void testGetAllProducts() {
        // Clear existing products
        productRepository.deleteAll();
        
        // Add test products
        productRepository.save(new Product("Product 1", "Description 1", 10.0, true));
        productRepository.save(new Product("Product 2", "Description 2", 20.0, false));
        
        // Get all products
        List<Product> products = productService.getAllProducts();
        
        // Verify that all products are returned
        assertThat(products).hasSize(2);
        assertThat(products).extracting(Product::getName).containsExactlyInAnyOrder("Product 1", "Product 2");
    }

    @Test
    void testGetAvailableProducts() {
        // Clear existing products
        productRepository.deleteAll();
        
        // Add test products
        productRepository.save(new Product("Product 1", "Description 1", 10.0, true));
        productRepository.save(new Product("Product 2", "Description 2", 20.0, false));
        
        // Get available products
        List<Product> availableProducts = productService.getAvailableProducts();
        
        // Verify that only available products are returned
        assertThat(availableProducts).hasSize(1);
        assertThat(availableProducts).extracting(Product::getName).containsExactly("Product 1");
    }

    @Test
    void testGetSortedProductsByPrice() {
        // Clear existing products
        productRepository.deleteAll();
        
        // Add test products in unsorted order
        productRepository.save(new Product("Product 3", "Description 3", 30.0, true));
        productRepository.save(new Product("Product 1", "Description 1", 10.0, true));
        productRepository.save(new Product("Product 2", "Description 2", 20.0, true));
        
        // Get sorted products
        List<Product> sortedProducts = productService.getSortedProductsByPrice();
        
        // Verify that products are sorted by price
        assertThat(sortedProducts).hasSize(3);
        assertThat(sortedProducts).extracting(Product::getPrice)
                                 .containsExactly(10.0, 20.0, 30.0);
    }

    @Test
    void testCalculateTotalInventoryValue() {
        // Clear existing products
        productRepository.deleteAll();
        
        // Add test products
        productRepository.save(new Product("Product 1", "Description 1", 10.0, true));
        productRepository.save(new Product("Product 2", "Description 2", 20.0, false));
        productRepository.save(new Product("Product 3", "Description 3", 30.0, true));
        
        // Calculate inventory value
        Double inventoryValue = productService.calculateTotalInventoryValue();
        
        // Verify that the inventory value is calculated correctly
        assertThat(inventoryValue).isEqualTo(60.0);
    }

    @Test
    void testRestApiEndpoints() {
        // Test GET /api/products
        ResponseEntity<Product[]> response = restTemplate.getForEntity(
                "http://localhost:" + port + "/api/products", Product[].class);
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(response.getBody()).isNotNull();
        
        // Test GET /api/products/sorted
        ResponseEntity<Product[]> sortedResponse = restTemplate.getForEntity(
                "http://localhost:" + port + "/api/products/sorted", Product[].class);
        assertThat(sortedResponse.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(sortedResponse.getBody()).isNotNull();
        
        // Test GET /api/products/available
        ResponseEntity<Product[]> availableResponse = restTemplate.getForEntity(
                "http://localhost:" + port + "/api/products/available", Product[].class);
        assertThat(availableResponse.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(availableResponse.getBody()).isNotNull();
        
        // Test GET /api/products/inventory-value
        ResponseEntity<Double> inventoryResponse = restTemplate.getForEntity(
                "http://localhost:" + port + "/api/products/inventory-value", Double.class);
        assertThat(inventoryResponse.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(inventoryResponse.getBody()).isNotNull();
    }
}
