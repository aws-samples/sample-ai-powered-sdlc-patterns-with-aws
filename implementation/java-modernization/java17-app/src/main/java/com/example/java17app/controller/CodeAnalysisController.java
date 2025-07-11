package com.example.java17app.controller;

import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;

import java.util.HashMap;
import java.util.Map;

@Controller
public class CodeAnalysisController {

    @GetMapping("/code-analysis")
    public String codeAnalysis(Model model) {
        // Java 17 features analysis
        var java17Features = new HashMap<String, String>();
        java17Features.put("Lambda Expressions", 
            "Lambda expressions are used in the ProductService class for sorting products by price.");
        java17Features.put("Stream API", 
            "Stream API is used for filtering and mapping collections in the getAvailableProducts method.");
        java17Features.put("Modern Exception Handling", 
            "Improved exception handling with proper logging in calculateTotalInventoryValue method.");
        java17Features.put("JPA Annotations", 
            "Using jakarta.persistence annotations instead of javax.persistence.");
        java17Features.put("Date-Time API", 
            "Using java.time.LocalDateTime instead of the legacy java.util.Date API.");
        
        // Code structure analysis
        var codeStructure = new HashMap<String, String>();
        codeStructure.put("Model", 
            "Product class with JPA annotations and traditional getters/setters.");
        codeStructure.put("Repository", 
            "ProductRepository interface extending JpaRepository for database operations.");
        codeStructure.put("Service", 
            "ProductService class with business logic and Java 17 features.");
        codeStructure.put("Controller", 
            "REST API endpoints in ProductController and web views in HomeController.");
        codeStructure.put("Configuration", 
            "DataInitializer for sample data and application.properties for configuration.");
        
        // Java 17 features used
        var java17FeaturesUsed = new HashMap<String, String>();
        java17FeaturesUsed.put("Lambda Expressions", 
            "Used for concise implementation of functional interfaces.");
        java17FeaturesUsed.put("Stream API", 
            "Used for processing collections of objects in a functional style.");
        java17FeaturesUsed.put("Local Variable Type Inference", 
            "Using 'var' keyword for local variable type inference.");
        java17FeaturesUsed.put("New Date-Time API", 
            "Using java.time package for better date and time handling.");
        java17FeaturesUsed.put("Optional API", 
            "Using Optional for better null handling in the service layer.");
        java17FeaturesUsed.put("Pattern Matching", 
            "Using pattern matching for instanceof checks.");
        java17FeaturesUsed.put("Text Blocks", 
            "Using text blocks for multiline strings.");
        java17FeaturesUsed.put("Enhanced Switch Expressions", 
            "Using switch expressions for more concise code.");
        
        model.addAttribute("java17Features", java17Features);
        model.addAttribute("codeStructure", codeStructure);
        model.addAttribute("java17FeaturesUsed", java17FeaturesUsed);
        
        return "code-analysis";
    }
}
