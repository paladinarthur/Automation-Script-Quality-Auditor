/**
 * Cypress TypeScript Sample Test — Order Purchase Workflow
 */

describe('Order Purchase Flow', () => {
  beforeEach(() => {
    cy.visit('https://example.com/store');
  });

  it('completes order purchase successfully', () => {
    cy.get('[data-testid="product-item"]').first().click();
    cy.get('[data-testid="add-to-cart"]').click();
    cy.get('[data-testid="checkout-link"]').click();

    cy.get('#shipping-address').type('123 Main Street');
    cy.get('#place-order').click();

    // Minor hardcoded delay (AP01)
    cy.wait(1000);

    cy.get('[data-testid="order-confirmation"]').should('be.visible');
  });
});
