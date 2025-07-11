package com.example.java8app.controller;

import com.example.java8app.model.Product;
import com.example.java8app.service.ProductService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.ModelAttribute;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PathVariable;

import java.util.List;

@Controller
public class HomeController {

    @Autowired
    private ProductService productService;

    @GetMapping("/")
    public String home(Model model) {
        model.addAttribute("products", productService.getAllProducts());
        model.addAttribute("availableProducts", productService.getAvailableProducts());
        model.addAttribute("sortedProducts", productService.getSortedProductsByPrice());
        model.addAttribute("inventoryValue", productService.calculateTotalInventoryValue());
        model.addAttribute("newProduct", new Product());
        return "home";
    }

    @PostMapping("/products")
    public String addProduct(@ModelAttribute Product product) {
        product.setCreatedDate(new java.util.Date());
        productService.createProduct(product);
        return "redirect:/";
    }

    @GetMapping("/products/delete/{id}")
    public String deleteProduct(@PathVariable Long id) {
        productService.deleteProduct(id);
        return "redirect:/";
    }
}
