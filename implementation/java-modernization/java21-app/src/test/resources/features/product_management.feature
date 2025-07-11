Feature: Product Management
  As a store administrator
  I want to manage products in the inventory
  So that I can keep track of available items and their details

  Background:
    Given the following products exist in the system:
      | id | name       | description                        | price   | available |
      | 1  | Laptop     | High-performance laptop with 16GB RAM | 1299.99 | true      |
      | 2  | Smartphone | Latest model with 128GB storage    | 899.99  | true      |
      | 3  | Headphones | Noise-cancelling wireless headphones | 249.99  | false     |

  Scenario: View all products
    When I request to view all products
    Then I should see a list of 3 products
    And the product with id 1 should have name "Laptop"
    And the product with id 2 should have name "Smartphone"
    And the product with id 3 should have name "Headphones"

  Scenario: View product details
    When I request to view product with id 1
    Then I should see product details with name "Laptop"
    And the product price should be 1299.99
    And the product should be available

  Scenario: Add a new product
    When I add a new product with the following details:
      | name      | description           | price  | available |
      | Monitor   | 27-inch 4K monitor    | 349.99 | true      |
    Then the product should be saved successfully
    And I should see a list of 4 products
    And the new product should have name "Monitor"

  Scenario: Update an existing product
    When I update product with id 1 with the following details:
      | name          | description                          | price   | available |
      | Gaming Laptop | High-performance gaming laptop       | 1499.99 | true      |
    Then the product should be updated successfully
    And the product with id 1 should have name "Gaming Laptop"
    And the product with id 1 should have price 1499.99

  Scenario: Delete a product
    When I delete product with id 3
    Then the product should be deleted successfully
    And I should see a list of 2 products
    And the list should not contain a product with id 3

  Scenario: View available products
    When I request to view available products
    Then I should see a list of 2 products
    And all products should be available

  Scenario: View products sorted by price
    When I request to view products sorted by price
    Then I should see a list of 3 products
    And the products should be sorted by price in ascending order

  Scenario: Calculate total inventory value
    When I request to calculate the total inventory value
    Then the total value should be 2449.97
