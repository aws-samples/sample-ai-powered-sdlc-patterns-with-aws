package com.example.java21app.controller;

import com.example.java21app.model.Product;
import com.example.java21app.service.ProductService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.ModelAttribute;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.servlet.mvc.support.RedirectAttributes;

import java.time.LocalDateTime;

/**
 * Controller for handling web form submissions for products.
 */
@Controller
public class WebProductController {

    private final ProductService productService;

    @Autowired
    public WebProductController(ProductService productService) {
        this.productService = productService;
    }

    /**
     * Handles the form submission for adding a new product.
     */
    @PostMapping("/products")
    public String addProduct(@ModelAttribute Product product, RedirectAttributes redirectAttributes) {
        // Set the creation date
        product.setCreatedDate(LocalDateTime.now());
        
        // Save the product
        productService.createProduct(product);
        
        // Add a success message
        redirectAttributes.addFlashAttribute("successMessage", "Product added successfully!");
        
        // Redirect to the home page
        return "redirect:/";
    }
    
    /**
     * Handles the deletion of a product from the web interface.
     */
    @GetMapping("/products/delete/{id}")
    public String deleteProduct(@PathVariable Long id, RedirectAttributes redirectAttributes) {
        productService.deleteProduct(id);
        redirectAttributes.addFlashAttribute("successMessage", "Product deleted successfully!");
        return "redirect:/";
    }
}
