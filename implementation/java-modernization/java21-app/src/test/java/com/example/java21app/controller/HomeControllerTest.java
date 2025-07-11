package com.example.java21app.controller;

import com.example.java21app.model.Product;
import com.example.java21app.service.ProductService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.ui.Model;

import java.time.LocalDateTime;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
public class HomeControllerTest {

    @Mock
    private ProductService productService;

    @Mock
    private Model model;

    @InjectMocks
    private HomeController homeController;

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
    void home_ShouldAddAttributesToModelAndReturnHomeView() {
        // Arrange
        when(productService.getAllProducts()).thenReturn(allProducts);
        when(productService.getSortedProductsByPrice()).thenReturn(sortedProducts);
        when(model.addAttribute(anyString(), any())).thenReturn(model);

        // Act
        String viewName = homeController.home(model);

        // Assert
        assertThat(viewName).isEqualTo("home");
        
        verify(productService, times(1)).getAllProducts();
        verify(productService, times(1)).getSortedProductsByPrice();
        
        verify(model).addAttribute(eq("products"), eq(allProducts));
        verify(model).addAttribute(eq("availableProducts"), any(List.class));
        verify(model).addAttribute(eq("sortedProducts"), eq(sortedProducts));
        verify(model).addAttribute(eq("availableCount"), eq(2));
        verify(model).addAttribute(eq("totalValue"), any(Double.class));
        verify(model).addAttribute(eq("newProduct"), any(Product.class));
    }
}
