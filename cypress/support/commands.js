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

Cypress.Commands.overwrite('log', (subject, message) => cy.task('log', message));


Cypress.Commands.add("pciLogin", (user) => {
  cy.clearCookies();

  cy.fixture("config").then((config) => {
    cy.visit(config.site_url);

    // homepage login button
    cy.get("#cyp-login-button").click();

    // fill  and submit login form
    cy.get("#auth_user_email").typeFast(user.mail);
    cy.get("#auth_user_password").typeFast(user.password);

    cy.get("input[type=submit]").click();

    // check if profile menu exist
    cy.contains(".dropdown-toggle", user.firstname).should("exist");
  });
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
        cy.contains(".dropdown-toggle", "For managers").click();
        cy.contains("a", "All articles").click();

        if (status != "not.exist")
          cy.contains("a", "View / Edit").first().click();
        // cy.screenshot()
        break;

      case "recommender":
        cy.contains(".dropdown-toggle", "For recommenders").click();
        cy.contains("a", "Preprint(s) you are handling").click();

        if (status != "not.exist")
          cy.contains("a", "View / Edit").first().click();
        // cy.screenshot()
        break;

      case "recommender-completed":
        cy.contains(".dropdown-toggle", "For recommenders").click();
        cy.contains("a", "Your completed evaluation(s)").click();
        cy.contains("a > span", "View").first().click();
        break;

      case "suggested_recommender":
        cy.contains(".dropdown-toggle", "For recommenders").click();
        cy.contains("a", "Request(s) to handle a preprint").click();

        if (status != "not.exist") cy.contains("a", "View").first().click();
        // cy.screenshot()
        break;

      case "reviewer":
        cy.contains(".dropdown-toggle", "For contributors").click();
        cy.contains("a", "Your reviews").click();

        if (status != "not.exist")
          cy.contains("a > span", "View").first().click();
        // cy.screenshot()
        break;

      case "suggested_reviewer":
        cy.contains(".dropdown-toggle", "For contributors").click();
        cy.contains("a", "Invitation(s) to review a preprint").click();

        if (status != "not.exist")
          cy.contains("a", "Accept or decline").first().click();
        // cy.screenshot()
        break;

      case "submitter":
        cy.contains(".dropdown-toggle", "For contributors").click();
        cy.contains("a", "Your submitted preprints").click();

        if (status != "not.exist")
          cy.contains("a", "View / Edit").first().click();
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
        if (role === "suggested_recommender")
          folder_name = test + "/recommender";
        cy.screenshot(folder_name + "/" + step + " - " + role);
        cy.wait(500);
      }

      cy.get(".pci-status-big").first().should("contain", status);
    }
  }
);

Cypress.Commands.add("pciDeleteWithTestLastArticle", (articleTitle) => {
  cy.fixture("users").then((user) => {
    cy.clearCookies();
    cy.pciLogin(user.manager);
  });

  cy.contains(".dropdown-toggle", "For managers").click();
  cy.contains("a", "All articles").click();

  cy.contains("tr", articleTitle).should("exist");

  cy.contains("a", "View / Edit").first().click();

  cy.contains("a", "Edit article").click();

  cy.get("#delete_record").click();

  cy.get("input[type=submit]").click();

  cy.contains("tr", articleTitle).should("not.exist");
});

Cypress.Commands.add(
  "typeFast",
  {
    prevSubject: true,
  },
  (subject, text) => {
    cy.wrap(subject).invoke("val", text).trigger("change");
  }
);

Cypress.Commands.add(
  "typeTinymce",
  {
    prevSubject: true,
  },
  (subject, html_text) => {
    // const iframe2 = cy.get(subject)

    cy.get(subject)
      .its("0.contentDocument")
      .should("exist")
      .its("body")
      .should("not.be.undefined")
      .then(cy.wrap)
      .invoke("prop", "innerHTML", html_text);

    // iframe2.contentDocument.get('body').innerHTML = html_text
  }
);

Cypress.Commands.add(
  "clearTinymce",
  {
    prevSubject: true,
  },
  (subject, html_text) => {
    // const iframe2 = cy.get(subject)

    cy.get(subject)
      .its("0.contentDocument")
      .should("exist")
      .its("body")
      .should("not.be.undefined")
      .then(cy.wrap)
      .invoke("prop", "innerHTML", "");

    // iframe2.contentDocument.get('body').innerHTML = html_text
  }
);
