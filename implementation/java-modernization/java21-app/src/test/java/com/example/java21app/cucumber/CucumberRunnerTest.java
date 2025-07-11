package com.example.java21app.cucumber;

import org.junit.platform.suite.api.ConfigurationParameter;
import org.junit.platform.suite.api.IncludeEngines;
import org.junit.platform.suite.api.SelectClasspathResource;
import org.junit.platform.suite.api.Suite;

import static io.cucumber.junit.platform.engine.Constants.PLUGIN_PROPERTY_NAME;
import static io.cucumber.junit.platform.engine.Constants.GLUE_PROPERTY_NAME;

@Suite
@IncludeEngines("cucumber")
@SelectClasspathResource("features")
@ConfigurationParameter(key = PLUGIN_PROPERTY_NAME, value = "pretty")
@ConfigurationParameter(key = PLUGIN_PROPERTY_NAME, value = "html:target/cucumber-reports/cucumber-pretty.html")
@ConfigurationParameter(key = PLUGIN_PROPERTY_NAME, value = "json:target/cucumber.json")
@ConfigurationParameter(key = GLUE_PROPERTY_NAME, value = "com.example.java21app.cucumber.steps")
public class CucumberRunnerTest {
    // This class is empty, it's just a runner for Cucumber tests using JUnit 5 Platform
}
