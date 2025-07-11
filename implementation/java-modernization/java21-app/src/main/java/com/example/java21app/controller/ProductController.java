package com.example.java21app.controller;

import com.example.java21app.dto.ProductDTO;
import com.example.java21app.model.Product;
import com.example.java21app.service.ProductService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/products")
public class ProductController {

    private final ProductService productService;

    @Autowired
    public ProductController(ProductService productService) {
        this.productService = productService;
    }

    @GetMapping
    public List<Product> getAllProducts() {
        return productService.getAllProducts();
    }

    @GetMapping("/{id}")
    public ResponseEntity<ProductDTO> getProductById(@PathVariable Long id) {
        var product = productService.getProductById(id);
        return (product != null) 
            ? ResponseEntity.ok(ProductDTO.fromProduct(product))
            : ResponseEntity.notFound().build();
    }

    @PostMapping
    public ProductDTO createProduct(@RequestBody ProductDTO productDTO) {
        var savedProduct = productService.createProduct(productDTO.toEntity());
        return ProductDTO.fromProduct(savedProduct);
    }

    @PutMapping("/{id}")
    public ResponseEntity<ProductDTO> updateProduct(@PathVariable Long id, @RequestBody ProductDTO productDTO) {
        var updatedProduct = productService.updateProduct(id, productDTO.toEntity());
        return (updatedProduct != null)
            ? ResponseEntity.ok(ProductDTO.fromProduct(updatedProduct))
            : ResponseEntity.notFound().build();
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteProduct(@PathVariable Long id) {
        productService.deleteProduct(id);
        return ResponseEntity.ok().build();
    }

    @GetMapping("/sorted")
    public List<ProductDTO> getSortedProducts() {
        return productService.getSortedProductsByPrice().stream()
            .map(ProductDTO::fromProduct)
            .toList();
    }

    @GetMapping("/available")
    public List<ProductDTO> getAvailableProducts() {
        return productService.getAvailableProducts().stream()
            .map(ProductDTO::fromProduct)
            .toList();
    }

    @GetMapping("/inventory-value")
    public Double getInventoryValue() {
        return productService.calculateTotalInventoryValue();
    }
    
    @GetMapping("/{id}/category")
    public String getProductCategory(@PathVariable Long id) {
        var product = productService.getProductById(id);
        return (product != null)
            ? productService.getProductCategory(product)
            : "Product not found";
    }
}
