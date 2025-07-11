package com.example.java8app.controller;

import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;

import java.util.HashMap;
import java.util.Map;

@Controller
public class CodeAnalysisController {

    @GetMapping("/code-analysis")
    public String codeAnalysis(Model model) {
        // Java 8 features analysis
        Map<String, String> java8Features = new HashMap<>();
        java8Features.put("Anonymous Inner Classes", 
            "Anonymous inner classes are used in the ProductService class for sorting products by price.");
        java8Features.put("Traditional For Loops", 
            "Traditional for loops are used instead of Stream API in the getAvailableProducts method.");
        java8Features.put("Old Exception Handling", 
            "Traditional try-catch blocks without try-with-resources in calculateTotalInventoryValue method.");
        java8Features.put("JPA Annotations", 
            "Using javax.persistence annotations instead of jakarta.persistence.");
        java8Features.put("Date API", 
            "Using java.util.Date instead of the modern Java 8 Date-Time API.");
        
        // Code structure analysis
        Map<String, String> codeStructure = new HashMap<>();
        codeStructure.put("Model", 
            "Product class with JPA annotations and traditional getters/setters.");
        codeStructure.put("Repository", 
            "ProductRepository interface extending JpaRepository for database operations.");
        codeStructure.put("Service", 
            "ProductService class with business logic and Java 8 features.");
        codeStructure.put("Controller", 
            "REST API endpoints in ProductController and web views in HomeController.");
        codeStructure.put("Configuration", 
            "DataInitializer for sample data and application.properties for configuration.");
        
        // Modernization opportunities
        Map<String, String> modernizationOpportunities = new HashMap<>();
        modernizationOpportunities.put("Lambda Expressions", 
            "Replace anonymous inner classes with lambda expressions.");
        modernizationOpportunities.put("Stream API", 
            "Replace traditional loops with Stream API for filtering and mapping.");
        modernizationOpportunities.put("Try-With-Resources", 
            "Use try-with-resources for better resource management.");
        modernizationOpportunities.put("New Date-Time API", 
            "Replace java.util.Date with java.time API.");
        modernizationOpportunities.put("Records", 
            "Use records for simple data carrier classes.");
        modernizationOpportunities.put("Pattern Matching", 
            "Implement pattern matching for instanceof.");
        modernizationOpportunities.put("Text Blocks", 
            "Use text blocks for multiline strings.");
        modernizationOpportunities.put("Switch Expressions", 
            "Use enhanced switch expressions.");
        
        model.addAttribute("java8Features", java8Features);
        model.addAttribute("codeStructure", codeStructure);
        model.addAttribute("modernizationOpportunities", modernizationOpportunities);
        
        return "code-analysis";
    }
}
