package com.example.java21app.cucumber.steps;

import com.example.java21app.model.Product;
import com.example.java21app.repository.ProductRepository;
import com.example.java21app.service.ProductService;
import io.cucumber.datatable.DataTable;
import io.cucumber.java.Before;
import io.cucumber.java.en.Given;
import io.cucumber.java.en.Then;
import io.cucumber.java.en.When;
import org.springframework.beans.factory.annotation.Autowired;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

public class ProductManagementSteps {

    @Autowired
    private ProductRepository productRepository;

    @Autowired
    private ProductService productService;

    private List<Product> resultProducts;
    private Product resultProduct;
    private Double totalValue;

    @Before
    public void setup() {
        productRepository.deleteAll();
    }

    @Given("the following products exist in the system:")
    public void theFollowingProductsExistInTheSystem(DataTable dataTable) {
        List<Map<String, String>> rows = dataTable.asMaps(String.class, String.class);
        
        for (Map<String, String> row : rows) {
            Product product = new Product();
            product.setId(Long.parseLong(row.get("id")));
            product.setName(row.get("name"));
            product.setDescription(row.get("description"));
            product.setPrice(Double.parseDouble(row.get("price")));
            product.setAvailable(Boolean.parseBoolean(row.get("available")));
            product.setCreatedDate(LocalDateTime.now());
            
            productRepository.save(product);
        }
    }

    @When("I request to view all products")
    public void iRequestToViewAllProducts() {
        resultProducts = productService.getAllProducts();
    }

    @Then("I should see a list of {int} products")
    public void iShouldSeeAListOfProducts(int count) {
        assertThat(resultProducts).hasSize(count);
    }

    @Then("the product with id {int} should have name {string}")
    public void theProductWithIdShouldHaveName(int id, String name) {
        Product product = resultProducts.stream()
                .filter(p -> p.getId() == id)
                .findFirst()
                .orElseThrow(() -> new AssertionError("Product with id " + id + " not found"));
        
        assertThat(product.getName()).isEqualTo(name);
    }

    @When("I request to view product with id {int}")
    public void iRequestToViewProductWithId(int id) {
        resultProduct = productService.getProductById((long) id);
    }

    @Then("I should see product details with name {string}")
    public void iShouldSeeProductDetailsWithName(String name) {
        assertThat(resultProduct).isNotNull();
        assertThat(resultProduct.getName()).isEqualTo(name);
    }

    @Then("the product price should be {double}")
    public void theProductPriceShouldBe(double price) {
        assertThat(resultProduct.getPrice()).isEqualTo(price);
    }

    @Then("the product should be available")
    public void theProductShouldBeAvailable() {
        assertThat(resultProduct.getAvailable()).isTrue();
    }

    @When("I add a new product with the following details:")
    public void iAddANewProductWithTheFollowingDetails(DataTable dataTable) {
        Map<String, String> row = dataTable.asMaps(String.class, String.class).get(0);
        
        Product newProduct = new Product();
        newProduct.setName(row.get("name"));
        newProduct.setDescription(row.get("description"));
        newProduct.setPrice(Double.parseDouble(row.get("price")));
        newProduct.setAvailable(Boolean.parseBoolean(row.get("available")));
        
        resultProduct = productService.createProduct(newProduct);
    }

    @Then("the product should be saved successfully")
    public void theProductShouldBeSavedSuccessfully() {
        assertThat(resultProduct).isNotNull();
        assertThat(resultProduct.getId()).isNotNull();
    }

    @Then("the new product should have name {string}")
    public void theNewProductShouldHaveName(String name) {
        assertThat(resultProduct.getName()).isEqualTo(name);
    }

    @When("I update product with id {int} with the following details:")
    public void iUpdateProductWithIdWithTheFollowingDetails(int id, DataTable dataTable) {
        Map<String, String> row = dataTable.asMaps(String.class, String.class).get(0);
        
        Product updateProduct = new Product();
        updateProduct.setName(row.get("name"));
        updateProduct.setDescription(row.get("description"));
        updateProduct.setPrice(Double.parseDouble(row.get("price")));
        updateProduct.setAvailable(Boolean.parseBoolean(row.get("available")));
        
        resultProduct = productService.updateProduct((long) id, updateProduct);
    }

    @Then("the product should be updated successfully")
    public void theProductShouldBeUpdatedSuccessfully() {
        assertThat(resultProduct).isNotNull();
    }

    @Then("the product with id {int} should have price {double}")
    public void theProductWithIdShouldHavePrice(int id, double price) {
        Product product = productService.getProductById((long) id);
        assertThat(product).isNotNull();
        assertThat(product.getPrice()).isEqualTo(price);
    }

    @When("I delete product with id {int}")
    public void iDeleteProductWithId(int id) {
        productService.deleteProduct((long) id);
    }

    @Then("the product should be deleted successfully")
    public void theProductShouldBeDeletedSuccessfully() {
        // This step is verified by the next step
    }

    @Then("the list should not contain a product with id {int}")
    public void theListShouldNotContainAProductWithId(int id) {
        Product product = productService.getProductById((long) id);
        assertThat(product).isNull();
    }

    @When("I request to view available products")
    public void iRequestToViewAvailableProducts() {
        resultProducts = productService.getAvailableProducts();
    }

    @Then("all products should be available")
    public void allProductsShouldBeAvailable() {
        assertThat(resultProducts).allMatch(Product::getAvailable);
    }

    @When("I request to view products sorted by price")
    public void iRequestToViewProductsSortedByPrice() {
        resultProducts = productService.getSortedProductsByPrice();
    }

    @Then("the products should be sorted by price in ascending order")
    public void theProductsShouldBeSortedByPriceInAscendingOrder() {
        List<Product> sortedList = new ArrayList<>(resultProducts);
        sortedList.sort(Comparator.comparing(Product::getPrice));
        
        assertThat(resultProducts).containsExactlyElementsOf(sortedList);
    }

    @When("I request to calculate the total inventory value")
    public void iRequestToCalculateTheTotalInventoryValue() {
        totalValue = productService.calculateTotalInventoryValue();
    }

    @Then("the total value should be {double}")
    public void theTotalValueShouldBe(double expectedValue) {
        assertThat(totalValue).isEqualTo(expectedValue);
    }
}
