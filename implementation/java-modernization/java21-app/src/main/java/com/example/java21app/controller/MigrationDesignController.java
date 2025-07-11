package com.example.java21app.controller;

import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;

@Controller
public class MigrationDesignController {

    @GetMapping("/migration-design")
    public String migrationDesign(Model model) {
        // Migration statistics
        model.addAttribute("totalTransformations", 15);
        model.addAttribute("performanceImprovement", 50);
        model.addAttribute("codeReduction", 30);
        model.addAttribute("securityEnhancements", 8);
        
        // Security statistics
        model.addAttribute("totalVulnerabilitiesBefore", 77);
        model.addAttribute("totalVulnerabilitiesAfter", 0);
        model.addAttribute("kevVulnerabilitiesBefore", 3);
        model.addAttribute("kevVulnerabilitiesAfter", 0);
        model.addAttribute("criticalVulnerabilitiesBefore", 6);
        model.addAttribute("criticalVulnerabilitiesAfter", 0);
        model.addAttribute("highVulnerabilitiesBefore", 28);
        model.addAttribute("highVulnerabilitiesAfter", 0);
        
        // Framework versions
        model.addAttribute("java8SpringBootVersion", "2.7.18");
        model.addAttribute("java17SpringBootVersion", "3.3.11");
        model.addAttribute("java21SpringBootVersion", "3.3.11");
        model.addAttribute("java8TomcatVersion", "9.0.99");
        model.addAttribute("java17TomcatVersion", "10.1.42");
        model.addAttribute("java21TomcatVersion", "10.1.42");
        model.addAttribute("h2Version", "2.2.224");
        model.addAttribute("snakeYamlVersion", "2.2");
        
        return "migration-design";
    }
}
