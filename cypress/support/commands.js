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
  cy.get("#auth_user_email").typeFast(user.mail);
  cy.get("#auth_user_password").typeFast(user.password);

  cy.get("input[type=submit]").click();

  // check if profile menu exist
  cy.contains(".dropdown-toggle", user.firstname).should("exist");
});

Cypress.Commands.add("pciLogout", () => {
  cy.contains(".dropdown-toggle", ".glyphicon-user").should("exist");
  cy.contains(".dropdown-toggle", ".glyphicon-user").click();

  cy.contains("a", "Log Out").click();

  cy.wait(500);
  cy.contains(".w2p_flash", "Logged out").should("exist");
});

Cypress.Commands.add(
  "pciCheckArticleStatus",
  (test, user, role, step, status, articleTitle) => {
    cy.clearCookies();
    cy.pciLogin(user);

    switch (role) {
      case "manager":
        cy.contains(".dropdown-toggle", "Manage").click();
        cy.contains("a", "All articles").click();

        if (status != "not.exist")
          cy.contains("a", "Check & Edit")
            .first()
            .click();
        // cy.screenshot()
        break;

      case "recommender":
        cy.contains(".dropdown-toggle", "Recommend").click();
        cy.contains("a", "Your recommendations of preprints").click();

        if (status != "not.exist")
          cy.contains("a", "Check & Edit")
            .first()
            .click();
        // cy.screenshot()
        break;

      case "suggested_recommender":
        cy.contains(".dropdown-toggle", "Recommend").click();
        cy.contains("a", "requests to handle a preprint").click();

        if (status != "not.exist")
          cy.contains("a", "View")
            .first()
            .click();
        // cy.screenshot()
        break;

      case "reviewer":
        cy.contains(".dropdown-toggle", "Contribute").click();
        cy.contains("a", "Your reviews").click();

        if (status != "not.exist")
          cy.contains("a", "View / Edit")
            .first()
            .click();
        // cy.screenshot()
        break;

      case "suggested_reviewer":
        cy.contains(".dropdown-toggle", "Contribute").click();
        cy.contains("a", "invitations to review a preprint").click();

        if (status != "not.exist")
          cy.contains("a", "Accept or decline")
            .first()
            .click();
        // cy.screenshot()
        break;

      case "submitter":
        cy.contains(".dropdown-toggle", "Contribute").click();
        cy.contains("a", "Your submitted preprints").click();

        if (status != "not.exist")
          cy.contains("a", "View / Edit")
            .first()
            .click();
        // cy.screenshot()
        break;
    }

    if (status == "not.exist") {
      cy.contains("tr", articleTitle).should("not.exist");
    } else {
      if (Cypress.env("withScreenshots")) {
        cy.wait(500);
        let folder_name = test + "/" + role;
        if (role === "suggested_reviewer") folder_name = test + "/reviewer";
        if (role === "suggested_recommender") folder_name = test + "/recommender";
        cy.screenshot(folder_name + "/" + step + " - " + role);
        cy.wait(500);
      }

      cy.get(".pci-status-big")
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

  cy.contains("a", "Edit article reference").click();

  cy.get("#delete_record").click();

  cy.get("input[type=submit]").click();

  cy.contains("tr", articleTitle).should("not.exist");
});

Cypress.Commands.add(
  "typeFast",
  {
    prevSubject: true
  },
  (subject, text) => {
    cy.wrap(subject)
      .invoke("val", text)
      .trigger("change");
  }
);
