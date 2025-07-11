package com.example.java21app.controller;

import com.example.java21app.model.Product;
import com.example.java21app.service.ProductService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * Controller for the home page and dashboard.
 */
@Controller
public class HomeController {

    private final ProductService productService;

    @Autowired
    public HomeController(ProductService productService) {
        this.productService = productService;
    }

    @GetMapping("/")
    public String home(Model model) {
        List<Product> products = productService.getAllProducts();
        
        // Using Java 21 Stream API features
        var availableProducts = products.stream()
            .filter(Product::getAvailable)
            .toList();
            
        var sortedProducts = productService.getSortedProductsByPrice();
            
        var totalValue = products.stream()
            .mapToDouble(Product::getPrice)
            .sum();
        
        // Add a new empty product for the form
        model.addAttribute("newProduct", new Product());
        
        model.addAttribute("products", products);
        model.addAttribute("availableProducts", availableProducts);
        model.addAttribute("sortedProducts", sortedProducts);
        model.addAttribute("availableCount", availableProducts.size());
        model.addAttribute("totalValue", totalValue);
        
        return "home";
    }
}
