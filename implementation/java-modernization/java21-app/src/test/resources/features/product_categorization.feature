Feature: Product Categorization
  As a store administrator
  I want to categorize products based on their price
  So that I can organize them for marketing and sales purposes

  Background:
    Given the following products exist in the system:
      | id | name       | description                        | price   | available |
      | 1  | Budget Item | Low-cost item                     | 9.99    | true      |
      | 2  | Standard Item | Mid-range item                  | 49.99   | true      |
      | 3  | Premium Item | High-end item                    | 99.99   | true      |
      | 4  | Luxury Item | Expensive item                    | 1299.99 | true      |

  Scenario: Categorize budget products
    When I request the category for product with id 1
    Then the product category should be "Budget"

  Scenario: Categorize standard products
    When I request the category for product with id 2
    Then the product category should be "Standard"

  Scenario: Categorize premium products
    When I request the category for product with id 3
    Then the product category should be "Premium"

  Scenario: Categorize luxury products
    When I request the category for product with id 4
    Then the product category should be "Luxury"

  Scenario: Get product information using pattern matching
    When I request information for product with id 4
    Then I should receive formatted product information
    And the information should contain "ID: 4"
    And the information should contain "Name: Luxury Item"
    And the information should contain "Price: $1299.99"
    And the information should contain "Available: Yes"
