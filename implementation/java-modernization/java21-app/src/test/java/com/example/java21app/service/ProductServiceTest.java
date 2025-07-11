package com.example.java21app.service;

import com.example.java21app.model.Product;
import com.example.java21app.repository.ProductRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
public class ProductServiceTest {

    @Mock
    private ProductRepository productRepository;

    @InjectMocks
    private ProductService productService;

    private Product laptop;
    private Product smartphone;
    private Product headphones;

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
    }

    @Test
    void getAllProducts_ShouldReturnAllProducts() {
        // Arrange
        when(productRepository.findAll()).thenReturn(List.of(laptop, smartphone, headphones));

        // Act
        List<Product> result = productService.getAllProducts();

        // Assert
        assertThat(result).hasSize(3);
        assertThat(result).contains(laptop, smartphone, headphones);
        verify(productRepository, times(1)).findAll();
    }

    @Test
    void getProductById_WithExistingId_ShouldReturnProduct() {
        // Arrange
        when(productRepository.findById(1L)).thenReturn(Optional.of(laptop));

        // Act
        Product result = productService.getProductById(1L);

        // Assert
        assertThat(result).isNotNull();
        assertThat(result.getId()).isEqualTo(1L);
        assertThat(result.getName()).isEqualTo("Laptop");
        verify(productRepository, times(1)).findById(1L);
    }

    @Test
    void getProductById_WithNonExistingId_ShouldReturnNull() {
        // Arrange
        when(productRepository.findById(99L)).thenReturn(Optional.empty());

        // Act
        Product result = productService.getProductById(99L);

        // Assert
        assertThat(result).isNull();
        verify(productRepository, times(1)).findById(99L);
    }

    @Test
    void createProduct_ShouldSaveAndReturnProduct() {
        // Arrange
        Product newProduct = new Product("Tablet", "10-inch tablet", 499.99, true);
        when(productRepository.save(any(Product.class))).thenReturn(newProduct);

        // Act
        Product result = productService.createProduct(newProduct);

        // Assert
        assertThat(result).isNotNull();
        assertThat(result.getName()).isEqualTo("Tablet");
        verify(productRepository, times(1)).save(newProduct);
    }

    @Test
    void updateProduct_WithExistingId_ShouldUpdateAndReturnProduct() {
        // Arrange
        Product updatedDetails = new Product("Updated Laptop", "Updated description", 1499.99, false);
        when(productRepository.findById(1L)).thenReturn(Optional.of(laptop));
        when(productRepository.save(any(Product.class))).thenAnswer(invocation -> invocation.getArgument(0));

        // Act
        Product result = productService.updateProduct(1L, updatedDetails);

        // Assert
        assertThat(result).isNotNull();
        assertThat(result.getName()).isEqualTo("Updated Laptop");
        assertThat(result.getDescription()).isEqualTo("Updated description");
        assertThat(result.getPrice()).isEqualTo(1499.99);
        assertThat(result.getAvailable()).isFalse();
        verify(productRepository, times(1)).findById(1L);
        verify(productRepository, times(1)).save(any(Product.class));
    }

    @Test
    void updateProduct_WithNonExistingId_ShouldReturnNull() {
        // Arrange
        Product updatedDetails = new Product("Updated Laptop", "Updated description", 1499.99, false);
        when(productRepository.findById(99L)).thenReturn(Optional.empty());

        // Act
        Product result = productService.updateProduct(99L, updatedDetails);

        // Assert
        assertThat(result).isNull();
        verify(productRepository, times(1)).findById(99L);
        verify(productRepository, never()).save(any(Product.class));
    }

    @Test
    void deleteProduct_ShouldCallRepositoryDeleteById() {
        // Arrange
        doNothing().when(productRepository).deleteById(1L);

        // Act
        productService.deleteProduct(1L);

        // Assert
        verify(productRepository, times(1)).deleteById(1L);
    }

    @Test
    void getSortedProductsByPrice_ShouldReturnProductsSortedByPrice() {
        // Arrange
        when(productRepository.findAll()).thenReturn(List.of(laptop, smartphone, headphones));

        // Act
        List<Product> result = productService.getSortedProductsByPrice();

        // Assert
        assertThat(result).hasSize(3);
        assertThat(result.get(0)).isEqualTo(headphones); // Lowest price
        assertThat(result.get(1)).isEqualTo(smartphone); // Middle price
        assertThat(result.get(2)).isEqualTo(laptop);     // Highest price
        verify(productRepository, times(1)).findAll();
    }

    @Test
    void getAvailableProducts_ShouldReturnOnlyAvailableProducts() {
        // Arrange
        when(productRepository.findAll()).thenReturn(List.of(laptop, smartphone, headphones));

        // Act
        List<Product> result = productService.getAvailableProducts();

        // Assert
        assertThat(result).hasSize(2);
        assertThat(result).contains(laptop, smartphone);
        assertThat(result).doesNotContain(headphones);
        verify(productRepository, times(1)).findAll();
    }

    @Test
    void calculateTotalInventoryValue_ShouldReturnSumOfAllProductPrices() {
        // Arrange
        when(productRepository.findAll()).thenReturn(List.of(laptop, smartphone, headphones));
        double expectedTotal = laptop.getPrice() + smartphone.getPrice() + headphones.getPrice();

        // Act
        Double result = productService.calculateTotalInventoryValue();

        // Assert
        assertThat(result).isEqualTo(expectedTotal);
        verify(productRepository, times(1)).findAll();
    }

    @Test
    void calculateTotalInventoryValue_WithException_ShouldReturnZero() {
        // Arrange
        when(productRepository.findAll()).thenThrow(new RuntimeException("Database error"));

        // Act
        Double result = productService.calculateTotalInventoryValue();

        // Assert
        assertThat(result).isEqualTo(0.0);
        verify(productRepository, times(1)).findAll();
    }

    @Test
    void getProductInfo_WithProductObject_ShouldReturnFormattedInfo() {
        // Act
        String result = productService.getProductInfo(laptop);

        // Assert
        assertThat(result).contains("Product Information:");
        assertThat(result).contains("ID: 1");
        assertThat(result).contains("Name: Laptop");
        assertThat(result).contains("Price: $1299.99");
        assertThat(result).contains("Available: Yes");
    }

    @Test
    void getProductInfo_WithNonProductObject_ShouldReturnErrorMessage() {
        // Act
        String result = productService.getProductInfo("Not a product");

        // Assert
        assertThat(result).isEqualTo("Not a valid product");
    }

    @Test
    void getProductCategory_WithBudgetPrice_ShouldReturnBudgetCategory() {
        // Arrange
        Product budgetProduct = new Product("Budget Item", "Cheap item", 9.99, true);

        // Act
        String result = productService.getProductCategory(budgetProduct);

        // Assert
        assertThat(result).isEqualTo("Budget");
    }

    @Test
    void getProductCategory_WithStandardPrice_ShouldReturnStandardCategory() {
        // Arrange
        Product standardProduct = new Product("Standard Item", "Standard item", 49.99, true);

        // Act
        String result = productService.getProductCategory(standardProduct);

        // Assert
        assertThat(result).isEqualTo("Standard");
    }

    @Test
    void getProductCategory_WithPremiumPrice_ShouldReturnPremiumCategory() {
        // Arrange
        Product premiumProduct = new Product("Premium Item", "Premium item", 99.99, true);

        // Act
        String result = productService.getProductCategory(premiumProduct);

        // Assert
        assertThat(result).isEqualTo("Premium");
    }

    @Test
    void getProductCategory_WithLuxuryPrice_ShouldReturnLuxuryCategory() {
        // Arrange
        // laptop is already set up with price 1299.99

        // Act
        String result = productService.getProductCategory(laptop);

        // Assert
        assertThat(result).isEqualTo("Luxury");
    }
}
