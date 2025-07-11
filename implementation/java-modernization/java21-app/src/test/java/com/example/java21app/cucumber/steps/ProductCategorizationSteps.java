package com.example.java21app.cucumber.steps;

import com.example.java21app.model.Product;
import com.example.java21app.service.ProductService;
import io.cucumber.java.en.Then;
import io.cucumber.java.en.When;
import org.springframework.beans.factory.annotation.Autowired;

import static org.assertj.core.api.Assertions.assertThat;

public class ProductCategorizationSteps {

    @Autowired
    private ProductService productService;

    private String productCategory;
    private String productInfo;

    @When("I request the category for product with id {int}")
    public void iRequestTheCategoryForProductWithId(int id) {
        Product product = productService.getProductById((long) id);
        productCategory = productService.getProductCategory(product);
    }

    @Then("the product category should be {string}")
    public void theProductCategoryShouldBe(String category) {
        assertThat(productCategory).isEqualTo(category);
    }

    @When("I request information for product with id {int}")
    public void iRequestInformationForProductWithId(int id) {
        Product product = productService.getProductById((long) id);
        productInfo = productService.getProductInfo(product);
    }

    @Then("I should receive formatted product information")
    public void iShouldReceiveFormattedProductInformation() {
        assertThat(productInfo).isNotNull();
        assertThat(productInfo).contains("Product Information:");
    }

    @Then("the information should contain {string}")
    public void theInformationShouldContain(String text) {
        assertThat(productInfo).contains(text);
    }
}
