package com.example.java21app.cucumber;

import com.example.java21app.Java21Application;
import io.cucumber.spring.CucumberContextConfiguration;
import org.springframework.boot.test.context.SpringBootTest;

@CucumberContextConfiguration
@SpringBootTest(classes = Java21Application.class, webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
public class CucumberSpringConfiguration {
    // This class is empty, it's just a configuration for Cucumber with Spring
}
