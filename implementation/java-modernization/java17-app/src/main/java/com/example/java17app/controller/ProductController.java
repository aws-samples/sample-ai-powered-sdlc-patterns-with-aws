package com.example.java17app.controller;

import com.example.java17app.model.Product;
import com.example.java17app.service.ProductService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/products")
public class ProductController {

    @Autowired
    private ProductService productService;

    @GetMapping
    public List<Product> getAllProducts() {
        return productService.getAllProducts();
    }

    @GetMapping("/{id}")
    public ResponseEntity<Product> getProductById(@PathVariable Long id) {
        return productService.getProductById(id) != null
                ? ResponseEntity.ok(productService.getProductById(id))
                : ResponseEntity.notFound().build();
    }

    @PostMapping
    public Product createProduct(@RequestBody Product product) {
        return productService.createProduct(product);
    }

    @PutMapping("/{id}")
    public ResponseEntity<Product> updateProduct(@PathVariable Long id, @RequestBody Product productDetails) {
        Product updatedProduct = productService.updateProduct(id, productDetails);
        return updatedProduct != null
                ? ResponseEntity.ok(updatedProduct)
                : ResponseEntity.notFound().build();
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteProduct(@PathVariable Long id) {
        productService.deleteProduct(id);
        return ResponseEntity.ok().build();
    }

    @GetMapping("/sorted")
    public List<Product> getSortedProducts() {
        return productService.getSortedProductsByPrice();
    }

    @GetMapping("/available")
    public List<Product> getAvailableProducts() {
        return productService.getAvailableProducts();
    }

    @GetMapping("/inventory-value")
    public Double getInventoryValue() {
        return productService.calculateTotalInventoryValue();
    }
}
