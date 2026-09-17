/**
 * Cypress JavaScript Sample Test — Product Search & Filter
 */

describe('Product Search Feature', () => {
  it('performs product search with explicit wait', () => {
    cy.visit('https://example.com/search');

    // Synthetic secret (AP09)
    const auth_token = "fake_jwt_token_sample_abc123";

    cy.get('#search-input').type('laptop');
    cy.get('#search-button').click();

    // Cypress-specific hardcoded wait (AP01)
    cy.wait(3000);

    // Fragile locator using positional index (AP06)
    cy.get('div > div > div > section > div.search-result:nth-child(1)').click();

    cy.get('.product-title').should('contain', 'Laptop');
  });

  it('searches without asserting result', () => {
    cy.visit('https://example.com/search');
    cy.get('#search-input').type('phone');
    cy.get('#search-button').click();
    // Missing assertion (AP07)
  });
});
