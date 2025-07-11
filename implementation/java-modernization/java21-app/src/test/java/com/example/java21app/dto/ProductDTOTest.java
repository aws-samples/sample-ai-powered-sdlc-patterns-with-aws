package com.example.java21app.dto;

import com.example.java21app.model.Product;
import org.junit.jupiter.api.Test;

import java.time.LocalDateTime;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

public class ProductDTOTest {

    @Test
    void constructor_WithValidData_ShouldCreateDTO() {
        // Act
        ProductDTO dto = new ProductDTO(1L, "Test Product", "Description", 99.99, LocalDateTime.now(), true);
        
        // Assert
        assertThat(dto.id()).isEqualTo(1L);
        assertThat(dto.name()).isEqualTo("Test Product");
        assertThat(dto.description()).isEqualTo("Description");
        assertThat(dto.price()).isEqualTo(99.99);
        assertThat(dto.available()).isTrue();
    }
    
    @Test
    void constructor_WithNullName_ShouldThrowException() {
        // Act & Assert
        assertThatThrownBy(() -> 
            new ProductDTO(1L, null, "Description", 99.99, LocalDateTime.now(), true)
        )
        .isInstanceOf(IllegalArgumentException.class)
        .hasMessageContaining("Product name cannot be empty");
    }
    
    @Test
    void constructor_WithEmptyName_ShouldThrowException() {
        // Act & Assert
        assertThatThrownBy(() -> 
            new ProductDTO(1L, "", "Description", 99.99, LocalDateTime.now(), true)
        )
        .isInstanceOf(IllegalArgumentException.class)
        .hasMessageContaining("Product name cannot be empty");
    }
    
    @Test
    void constructor_WithNullPrice_ShouldThrowException() {
        // Act & Assert
        assertThatThrownBy(() -> 
            new ProductDTO(1L, "Test Product", "Description", null, LocalDateTime.now(), true)
        )
        .isInstanceOf(IllegalArgumentException.class)
        .hasMessageContaining("Price cannot be negative");
    }
    
    @Test
    void constructor_WithNegativePrice_ShouldThrowException() {
        // Act & Assert
        assertThatThrownBy(() -> 
            new ProductDTO(1L, "Test Product", "Description", -10.0, LocalDateTime.now(), true)
        )
        .isInstanceOf(IllegalArgumentException.class)
        .hasMessageContaining("Price cannot be negative");
    }
    
    @Test
    void fromProduct_WithValidProduct_ShouldCreateDTO() {
        // Arrange
        Product product = new Product("Test Product", "Description", 99.99, true);
        product.setId(1L);
        LocalDateTime now = LocalDateTime.now();
        product.setCreatedDate(now);
        
        // Act
        ProductDTO dto = ProductDTO.fromProduct(product);
        
        // Assert
        assertThat(dto.id()).isEqualTo(1L);
        assertThat(dto.name()).isEqualTo("Test Product");
        assertThat(dto.description()).isEqualTo("Description");
        assertThat(dto.price()).isEqualTo(99.99);
        assertThat(dto.createdDate()).isEqualTo(now);
        assertThat(dto.available()).isTrue();
    }
    
    @Test
    void fromProduct_WithNullProduct_ShouldThrowException() {
        // Act & Assert
        assertThatThrownBy(() -> 
            ProductDTO.fromProduct(null)
        )
        .isInstanceOf(IllegalArgumentException.class)
        .hasMessageContaining("Product cannot be null");
    }
    
    @Test
    void fromProduct_WithNonProductObject_ShouldThrowException() {
        // Act & Assert
        assertThatThrownBy(() -> 
            ProductDTO.fromProduct("Not a product")
        )
        .isInstanceOf(IllegalArgumentException.class)
        .hasMessageContaining("Not a valid product object");
    }
    
    @Test
    void toEntity_ShouldConvertDTOToProduct() {
        // Arrange
        LocalDateTime now = LocalDateTime.now();
        ProductDTO dto = new ProductDTO(1L, "Test Product", "Description", 99.99, now, true);
        
        // Act
        Product product = dto.toEntity();
        
        // Assert
        assertThat(product.getId()).isEqualTo(1L);
        assertThat(product.getName()).isEqualTo("Test Product");
        assertThat(product.getDescription()).isEqualTo("Description");
        assertThat(product.getPrice()).isEqualTo(99.99);
        assertThat(product.getCreatedDate()).isEqualTo(now);
        assertThat(product.getAvailable()).isTrue();
    }
}
