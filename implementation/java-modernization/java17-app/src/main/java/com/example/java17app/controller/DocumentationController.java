package com.example.java17app.controller;

import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Controller
public class DocumentationController {

    @GetMapping("/requirements")
    public String requirements(Model model) {
        // Define use cases
        var useCases = new ArrayList<Map<String, String>>();
        
        var useCase1 = new HashMap<String, String>();
        useCase1.put("id", "UC-1");
        useCase1.put("name", "View Product Catalog");
        useCase1.put("actor", "Customer");
        useCase1.put("description", "User can view the list of all available products");
        useCase1.put("preconditions", "User has accessed the application");
        useCase1.put("mainFlow", "1. User navigates to the home page\n2. System displays all products\n3. User can view product details");
        useCase1.put("alternativeFlow", "2a. If no products are available, system displays empty list message");
        useCase1.put("postconditions", "User has viewed the product catalog");
        useCases.add(useCase1);
        
        var useCase2 = new HashMap<String, String>();
        useCase2.put("id", "UC-2");
        useCase2.put("name", "Add New Product");
        useCase2.put("actor", "Administrator");
        useCase2.put("description", "Administrator can add a new product to the catalog");
        useCase2.put("preconditions", "Administrator has accessed the application");
        useCase2.put("mainFlow", "1. Administrator fills in product details in the form\n2. Administrator submits the form\n3. System validates the input\n4. System adds the product to the database\n5. System displays updated product list");
        useCase2.put("alternativeFlow", "3a. If validation fails, system displays error message and returns to form");
        useCase2.put("postconditions", "New product is added to the catalog");
        useCases.add(useCase2);
        
        var useCase3 = new HashMap<String, String>();
        useCase3.put("id", "UC-3");
        useCase3.put("name", "Delete Product");
        useCase3.put("actor", "Administrator");
        useCase3.put("description", "Administrator can remove a product from the catalog");
        useCase3.put("preconditions", "Administrator has accessed the application and products exist");
        useCase3.put("mainFlow", "1. Administrator views the product list\n2. Administrator clicks delete button for a product\n3. System removes the product from the database\n4. System displays updated product list");
        useCase3.put("alternativeFlow", "3a. If deletion fails, system displays error message");
        useCase3.put("postconditions", "Product is removed from the catalog");
        useCases.add(useCase3);
        
        var useCase4 = new HashMap<String, String>();
        useCase4.put("id", "UC-4");
        useCase4.put("name", "View Available Products");
        useCase4.put("actor", "Customer");
        useCase4.put("description", "User can view only the products that are marked as available");
        useCase4.put("preconditions", "User has accessed the application");
        useCase4.put("mainFlow", "1. User navigates to the home page\n2. System displays available products section\n3. User can view available products");
        useCase4.put("alternativeFlow", "2a. If no available products exist, system displays empty list message");
        useCase4.put("postconditions", "User has viewed the available products");
        useCases.add(useCase4);
        
        var useCase5 = new HashMap<String, String>();
        useCase5.put("id", "UC-5");
        useCase5.put("name", "View Products Sorted by Price");
        useCase5.put("actor", "Customer");
        useCase5.put("description", "User can view products sorted by price from lowest to highest");
        useCase5.put("preconditions", "User has accessed the application");
        useCase5.put("mainFlow", "1. User navigates to the home page\n2. System displays products sorted by price section\n3. User can view sorted products");
        useCase5.put("alternativeFlow", "2a. If no products exist, system displays empty list message");
        useCase5.put("postconditions", "User has viewed the products sorted by price");
        useCases.add(useCase5);
        
        // Define functional requirements
        var functionalRequirements = new ArrayList<Map<String, String>>();
        
        var req1 = new HashMap<String, String>();
        req1.put("id", "FR-1");
        req1.put("name", "Product Management");
        req1.put("description", "The system shall allow administrators to add, view, and delete products");
        req1.put("priority", "High");
        functionalRequirements.add(req1);
        
        var req2 = new HashMap<String, String>();
        req2.put("id", "FR-2");
        req2.put("name", "Product Filtering");
        req2.put("description", "The system shall allow users to view only available products");
        req2.put("priority", "Medium");
        functionalRequirements.add(req2);
        
        var req3 = new HashMap<String, String>();
        req3.put("id", "FR-3");
        req3.put("name", "Product Sorting");
        req3.put("description", "The system shall allow users to view products sorted by price");
        req3.put("priority", "Medium");
        functionalRequirements.add(req3);
        
        var req4 = new HashMap<String, String>();
        req4.put("id", "FR-4");
        req4.put("name", "Inventory Value Calculation");
        req4.put("description", "The system shall calculate and display the total value of all products in inventory");
        req4.put("priority", "Low");
        functionalRequirements.add(req4);
        
        var req5 = new HashMap<String, String>();
        req5.put("id", "FR-5");
        req5.put("name", "Product Data Persistence");
        req5.put("description", "The system shall store product information in a database");
        req5.put("priority", "High");
        functionalRequirements.add(req5);
        
        // Define non-functional requirements
        var nonFunctionalRequirements = new ArrayList<Map<String, String>>();
        
        var nfr1 = new HashMap<String, String>();
        nfr1.put("id", "NFR-1");
        nfr1.put("name", "Performance");
        nfr1.put("description", "The system shall respond to user requests within 2 seconds");
        nfr1.put("priority", "Medium");
        nonFunctionalRequirements.add(nfr1);
        
        var nfr2 = new HashMap<String, String>();
        nfr2.put("id", "NFR-2");
        nfr2.put("name", "Usability");
        nfr2.put("description", "The system shall have an intuitive user interface that requires minimal training");
        nfr2.put("priority", "High");
        nonFunctionalRequirements.add(nfr2);
        
        var nfr3 = new HashMap<String, String>();
        nfr3.put("id", "NFR-3");
        nfr3.put("name", "Maintainability");
        nfr3.put("description", "The system shall be designed to allow easy modernization from Java 8 to Java 17");
        nfr3.put("priority", "High");
        nonFunctionalRequirements.add(nfr3);
        
        var nfr4 = new HashMap<String, String>();
        nfr4.put("id", "NFR-4");
        nfr4.put("name", "Compatibility");
        nfr4.put("description", "The system shall work on all major web browsers");
        nfr4.put("priority", "Medium");
        nonFunctionalRequirements.add(nfr4);
        
        model.addAttribute("useCases", useCases);
        model.addAttribute("functionalRequirements", functionalRequirements);
        model.addAttribute("nonFunctionalRequirements", nonFunctionalRequirements);
        
        return "requirements";
    }
    
    @GetMapping("/system-behavior")
    public String systemBehavior(Model model) {
        // Define system components
        var components = new ArrayList<Map<String, String>>();
        
        var comp1 = new HashMap<String, String>();
        comp1.put("name", "Web Layer");
        comp1.put("description", "Handles HTTP requests and responses, renders views, and manages user interaction");
        comp1.put("classes", "HomeController, ProductController, CodeAnalysisController, DocumentationController");
        components.add(comp1);
        
        var comp2 = new HashMap<String, String>();
        comp2.put("name", "Service Layer");
        comp2.put("description", "Implements business logic, processes data, and coordinates application activities");
        comp2.put("classes", "ProductService");
        components.add(comp2);
        
        var comp3 = new HashMap<String, String>();
        comp3.put("name", "Data Access Layer");
        comp3.put("description", "Manages database operations and provides an abstraction for data persistence");
        comp3.put("classes", "ProductRepository");
        components.add(comp3);
        
        var comp4 = new HashMap<String, String>();
        comp4.put("name", "Model Layer");
        comp4.put("description", "Represents business entities and data structures");
        comp4.put("classes", "Product");
        components.add(comp4);
        
        var comp5 = new HashMap<String, String>();
        comp5.put("name", "Configuration Layer");
        comp5.put("description", "Manages application configuration and initialization");
        comp5.put("classes", "DataInitializer");
        components.add(comp5);
        
        // Define system interactions
        var interactions = new ArrayList<Map<String, String>>();
        
        var int1 = new HashMap<String, String>();
        int1.put("name", "Add Product Flow");
        int1.put("description", "Process of adding a new product to the system");
        int1.put("sequence", "1. User submits product form (HomeController)\n2. Controller processes form data (HomeController)\n3. Service validates and saves product (ProductService)\n4. Repository persists product to database (ProductRepository)\n5. User is redirected to updated product list (HomeController)");
        interactions.add(int1);
        
        var int2 = new HashMap<String, String>();
        int2.put("name", "View Products Flow");
        int2.put("description", "Process of viewing all products");
        int2.put("sequence", "1. User requests home page (HomeController)\n2. Controller requests all products (ProductService)\n3. Service retrieves products from repository (ProductRepository)\n4. Controller adds products to model (HomeController)\n5. View renders product list (home.html)");
        interactions.add(int2);
        
        var int3 = new HashMap<String, String>();
        int3.put("name", "Delete Product Flow");
        int3.put("description", "Process of deleting a product");
        int3.put("sequence", "1. User clicks delete button (home.html)\n2. Controller receives delete request (HomeController)\n3. Service processes deletion (ProductService)\n4. Repository removes product from database (ProductRepository)\n5. User is redirected to updated product list (HomeController)");
        interactions.add(int3);
        
        model.addAttribute("components", components);
        model.addAttribute("interactions", interactions);
        
        return "system-behavior";
    }
}
