package com.example.java21app.controller;

import com.example.java21app.dto.ProductDTO;
import com.example.java21app.model.Product;
import com.example.java21app.service.ProductService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;

import java.time.LocalDateTime;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
public class ProductControllerTest {

    @Mock
    private ProductService productService;

    @InjectMocks
    private ProductController productController;

    private Product laptop;
    private Product smartphone;
    private Product headphones;
    private List<Product> allProducts;
    private List<Product> availableProducts;
    private List<Product> sortedProducts;

    @BeforeEach
    void setUp() {
        // Setup test data
        laptop = new Product("Laptop", "High-performance laptop with 16GB RAM", 1299.99, true);
        laptop.setId(1L);
        laptop.setCreatedDate(LocalDateTime.now());

        smartphone = new Product("Smartphone", "Latest model with 128GB storage", 899.99, true);
        smartphone.setId(2L);
        smartphone.setCreatedDate(LocalDateTime.now());

        headphones = new Product("Headphones", "Noise-cancelling wireless headphones", 249.99, false);
        headphones.setId(3L);
        headphones.setCreatedDate(LocalDateTime.now());

        allProducts = List.of(laptop, smartphone, headphones);
        availableProducts = List.of(laptop, smartphone);
        sortedProducts = List.of(headphones, smartphone, laptop); // Sorted by price
    }

    @Test
    void getAllProducts_ShouldReturnAllProducts() {
        // Arrange
        when(productService.getAllProducts()).thenReturn(allProducts);

        // Act
        List<Product> result = productController.getAllProducts();

        // Assert
        assertThat(result).hasSize(3);
        assertThat(result).isEqualTo(allProducts);
        verify(productService, times(1)).getAllProducts();
    }

    @Test
    void getProductById_WithExistingId_ShouldReturnProduct() {
        // Arrange
        when(productService.getProductById(1L)).thenReturn(laptop);

        // Act
        ResponseEntity<ProductDTO> response = productController.getProductById(1L);

        // Assert
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(response.getBody()).isNotNull();
        assertThat(response.getBody().id()).isEqualTo(1L);
        assertThat(response.getBody().name()).isEqualTo("Laptop");
        verify(productService, times(1)).getProductById(1L);
    }

    @Test
    void getProductById_WithNonExistingId_ShouldReturnNotFound() {
        // Arrange
        when(productService.getProductById(99L)).thenReturn(null);

        // Act
        ResponseEntity<ProductDTO> response = productController.getProductById(99L);

        // Assert
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.NOT_FOUND);
        assertThat(response.getBody()).isNull();
        verify(productService, times(1)).getProductById(99L);
    }

    @Test
    void createProduct_ShouldReturnCreatedProduct() {
        // Arrange
        ProductDTO inputDto = new ProductDTO(null, "New Product", "Description", 199.99, null, true);
        Product newProduct = inputDto.toEntity();
        newProduct.setId(4L);
        
        when(productService.createProduct(any(Product.class))).thenReturn(newProduct);

        // Act
        ProductDTO result = productController.createProduct(inputDto);

        // Assert
        assertThat(result).isNotNull();
        assertThat(result.id()).isEqualTo(4L);
        assertThat(result.name()).isEqualTo("New Product");
        verify(productService, times(1)).createProduct(any(Product.class));
    }

    @Test
    void updateProduct_WithExistingId_ShouldReturnUpdatedProduct() {
        // Arrange
        ProductDTO updateDto = new ProductDTO(1L, "Updated Laptop", "Updated description", 1499.99, null, false);
        Product updatedProduct = updateDto.toEntity();
        
        when(productService.updateProduct(eq(1L), any(Product.class))).thenReturn(updatedProduct);

        // Act
        ResponseEntity<ProductDTO> response = productController.updateProduct(1L, updateDto);

        // Assert
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(response.getBody()).isNotNull();
        assertThat(response.getBody().name()).isEqualTo("Updated Laptop");
        verify(productService, times(1)).updateProduct(eq(1L), any(Product.class));
    }

    @Test
    void updateProduct_WithNonExistingId_ShouldReturnNotFound() {
        // Arrange
        ProductDTO updateDto = new ProductDTO(99L, "Updated Product", "Updated description", 199.99, null, true);
        
        when(productService.updateProduct(eq(99L), any(Product.class))).thenReturn(null);

        // Act
        ResponseEntity<ProductDTO> response = productController.updateProduct(99L, updateDto);

        // Assert
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.NOT_FOUND);
        assertThat(response.getBody()).isNull();
        verify(productService, times(1)).updateProduct(eq(99L), any(Product.class));
    }

    @Test
    void deleteProduct_ShouldReturnOkResponse() {
        // Arrange
        doNothing().when(productService).deleteProduct(1L);

        // Act
        ResponseEntity<Void> response = productController.deleteProduct(1L);

        // Assert
        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.OK);
        verify(productService, times(1)).deleteProduct(1L);
    }

    @Test
    void getSortedProducts_ShouldReturnProductsSortedByPrice() {
        // Arrange
        when(productService.getSortedProductsByPrice()).thenReturn(sortedProducts);

        // Act
        List<ProductDTO> result = productController.getSortedProducts();

        // Assert
        assertThat(result).hasSize(3);
        assertThat(result.get(0).name()).isEqualTo("Headphones"); // Lowest price
        assertThat(result.get(1).name()).isEqualTo("Smartphone"); // Middle price
        assertThat(result.get(2).name()).isEqualTo("Laptop");     // Highest price
        verify(productService, times(1)).getSortedProductsByPrice();
    }

    @Test
    void getAvailableProducts_ShouldReturnOnlyAvailableProducts() {
        // Arrange
        when(productService.getAvailableProducts()).thenReturn(availableProducts);

        // Act
        List<ProductDTO> result = productController.getAvailableProducts();

        // Assert
        assertThat(result).hasSize(2);
        assertThat(result.get(0).name()).isEqualTo("Laptop");
        assertThat(result.get(1).name()).isEqualTo("Smartphone");
        verify(productService, times(1)).getAvailableProducts();
    }

    @Test
    void getInventoryValue_ShouldReturnTotalValue() {
        // Arrange
        double expectedTotal = 2449.97; // Sum of all product prices
        when(productService.calculateTotalInventoryValue()).thenReturn(expectedTotal);

        // Act
        Double result = productController.getInventoryValue();

        // Assert
        assertThat(result).isEqualTo(expectedTotal);
        verify(productService, times(1)).calculateTotalInventoryValue();
    }

    @Test
    void getProductCategory_WithExistingId_ShouldReturnCategory() {
        // Arrange
        when(productService.getProductById(1L)).thenReturn(laptop);
        when(productService.getProductCategory(laptop)).thenReturn("Luxury");

        // Act
        String result = productController.getProductCategory(1L);

        // Assert
        assertThat(result).isEqualTo("Luxury");
        verify(productService, times(1)).getProductById(1L);
        verify(productService, times(1)).getProductCategory(laptop);
    }

    @Test
    void getProductCategory_WithNonExistingId_ShouldReturnNotFoundMessage() {
        // Arrange
        when(productService.getProductById(99L)).thenReturn(null);

        // Act
        String result = productController.getProductCategory(99L);

        // Assert
        assertThat(result).isEqualTo("Product not found");
        verify(productService, times(1)).getProductById(99L);
        verify(productService, never()).getProductCategory(any());
    }
}
