package com.example.java21app.controller;

import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;

/**
 * Controller for the testing report page.
 */
@Controller
public class TestingReportController {

    @GetMapping("/testing-report")
    public String testingReport() {
        return "testing-report";
    }
}
