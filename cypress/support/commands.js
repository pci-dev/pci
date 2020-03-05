// ***********************************************
// This example commands.js shows you how to
// create various custom commands and overwrite
// existing commands.
//
// For more comprehensive examples of custom
// commands please read more here:
// https://on.cypress.io/custom-commands
// ***********************************************
//
//
// -- This is a parent command --
// Cypress.Commands.add("login", (email, password) => { ... })
//
//
// -- This is a child command --
// Cypress.Commands.add("drag", { prevSubject: 'element'}, (subject, options) => { ... })
//
//
// -- This is a dual command --
// Cypress.Commands.add("dismiss", { prevSubject: 'optional'}, (subject, options) => { ... })
//
//
// -- This will overwrite an existing command --
// Cypress.Commands.overwrite("visit", (originalFn, url, options) => { ... })

Cypress.Commands.add("pciLogin", user => {
  cy.clearCookies();
  cy.visit("http://127.0.0.1:8000/pcidev/");

  // homepage login button
  cy.get("#cyp-login-button").click();

  // fill  and submit login form
  cy.get("#auth_user_email").type(user.mail);
  cy.get("#auth_user_password").type(user.password);

  cy.get("input[type=submit]").click();

  // check if profile menu exist
  cy.contains(".dropdown-toggle", "Welcome ").should("exist");
});

Cypress.Commands.add("pciLogout", () => {
  cy.contains(".dropdown-toggle", "Welcome ").should("exist");
  cy.contains(".dropdown-toggle", "Welcome ").click();

  cy.contains("a", "Log Out").click();

  cy.wait(500);
  cy.contains(".w2p_flash", "Logged out").should("exist");
});

Cypress.Commands.add(
  "pciCheckArticleStatus",
  (user, role, status, articleTitle) => {
    
    cy.clearCookies();
    cy.pciLogin(user);

    switch (role) {
      case "manager":
        cy.contains(".dropdown-toggle", "Manage").click();
        cy.contains("a", "All articles").click();

        break;

      case "recommender":
        cy.contains(".dropdown-toggle", "Your Recommendations").click();
        cy.contains("a", "Your recommendations of preprints").click();
        break;

      case "suggested_recommender":
        cy.contains(".dropdown-toggle", "Your Recommendations").click();
        cy.contains("a", "requests to handle a preprint").click();
        break;

      case "reviewer":
        cy.contains(".dropdown-toggle", "Your contributions").click();
        cy.contains("a", "Your reviews").click();
        break;

      case "suggested_reviewer":
        cy.contains(".dropdown-toggle", "Your contributions").click();
        cy.contains("a", "invitations to review a preprint").click();
        break;

      case "submitter":
        cy.contains(".dropdown-toggle", "Your contributions").click();
        cy.contains("a", "Your submitted preprints").click();
        break;
    }

    if (status == "not.exist") {
      cy.contains("tr", articleTitle).should("not.exist");
    } else {
      cy.get(".pci-status")
        .first()
        .should("contain", status);
    }
  }
);

Cypress.Commands.add("pciDeleteWithTestLastArticle", articleTitle => {
  cy.fixture("users").then(user => {
    cy.clearCookies();
    cy.pciLogin(user.manager);
  });

  cy.contains(".dropdown-toggle", "Manage").click();
  cy.contains("a", "All articles").click();

  cy.contains("tr", articleTitle).should("exist");

  cy.contains("a", "Check & Edit")
    .first()
    .click();

  cy.contains("a", "Manage this request").click();

  cy.get("#delete_record").click();

  cy.get("input[type=submit]").click();

  cy.contains("tr", articleTitle).should("not.exist");
});