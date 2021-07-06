describe("Check toplevel pages", () => {

  describe("Help menu without login", () => {
    before(() => {
      cy.fixture("config").then((config) => {
	      cy.visit(config.site_url);
      });
    });

    it("Should show page help_generic", () => {
      cy.contains(".dropdown-toggle", "Help").click();
      cy.contains("a", "How does it work?").click();
      cy.contains(".pci-text-title", "How does it work?").should("exist");
    });

    it("Should show page guide_for_authors", () => {
      cy.contains(".dropdown-toggle", "Help").click();
      cy.contains("a", "Guide for Authors").click();
      cy.contains(".pci-text-title", "Guide for authors").should("exist");
    });

    it("Should show page guide_for_reviewers", () => {
      cy.contains(".dropdown-toggle", "Help").click();
      cy.contains("a", "Guide for Reviewers").click();
      cy.contains(".pci-text-title", "Guide for reviewers").should("exist");
    });

    it("Should show page guide_for_recommenders", () => {
      cy.contains(".dropdown-toggle", "Help").click();
      cy.contains("a", "Guide for Recommenders").click();
      cy.contains(".pci-text-title", "Guide for recommenders").should("exist");
    });

    it("Should show page become_a_recommenders", () => {
      cy.contains(".dropdown-toggle", "Help").click();
      cy.contains("a", "Become a Recommender").click();
      cy.contains(".pci-text-title", "Become a recommender").should("exist");
    });

    it("Should show page help_practical", () => {
      cy.contains(".dropdown-toggle", "Help").click();
      cy.contains("a", "How to ...?").click();
      cy.contains(".pci-text-title", "How to...?").should("exist");
    });

    it("Should show page faq", () => {
      cy.contains(".dropdown-toggle", "Help").click();
      cy.contains("a", "FAQs").click();
      cy.contains(".pci-text-title", "FAQs").should("exist");
    });

    it("Should show page cite", () => {
      cy.contains(".dropdown-toggle", "Help").click();
      cy.contains("a", "How should you cite an article?").click();
      cy.contains(".pci-text-title", "How should you cite an article?").should("exist");
    });

  });

  describe("Help URLs without login", () => {

    let site_url;

    before(() => {
      cy.fixture("config").then((config) => {
	      site_url = config.site_url;
      });
    });

    it("Should show page help_generic", () => {
      cy.visit(site_url + "help/help_generic");
      cy.contains(".pci-text-title", "How does it work?").should("exist");
    });

    it("Should show page guide_for_authors", () => {
      cy.visit(site_url + "help/guide_for_authors");
      cy.contains(".pci-text-title", "Guide for authors").should("exist");
    });

    it("Should show page guide_for_reviewers", () => {
      cy.visit(site_url + "help/guide_for_reviewers");
      cy.contains(".pci-text-title", "Guide for reviewers").should("exist");
    });

    it("Should show page guide_for_recommenders", () => {
      cy.visit(site_url + "help/guide_for_recommenders");
      cy.contains(".pci-text-title", "Guide for recommenders").should("exist");
    });

    it("Should show page become_a_recommenders", () => {
      cy.visit(site_url + "help/become_a_recommenders");
      cy.contains(".pci-text-title", "Become a recommender").should("exist");
    });

    it("Should show page help_practical", () => {
      cy.visit(site_url + "help/help_practical");
      cy.contains(".pci-text-title", "How to...?").should("exist");
    });

    it("Should show page faq", () => {
      cy.visit(site_url + "help/faq");
      cy.contains(".pci-text-title", "FAQs").should("exist");
    });

    it("Should show page cite", () => {
      cy.visit(site_url + "help/cite");
      cy.contains(".pci-text-title", "How should you cite an article?").should("exist");
    });

  });

  describe("Main URLs without login", () => {

    let site_url;

    before(() => {
      cy.fixture("config").then((config) => {
	      site_url = config.site_url;
      });
    });

    it("Should show page articles/", () => {
      cy.visit(site_url + "articles/");
      cy.contains(".pci-text-title", "Search articles").should("exist");
    });

    it("Should show page about/", () => {
      cy.visit(site_url + "about/");
      cy.contains(".pci-text-title", /^About /).should("exist");
    });

    it("Should show page help/", () => {
      cy.visit(site_url + "help/");
      cy.contains(".pci-text-title", "How does it work?").should("exist");
    });

  });

  describe("Main URLs with login", () => {

    let site_url;

    before(() => {
      cy.fixture("config").then((config) => {
        site_url = config.site_url;
      });
    });

    beforeEach(() => {
      cy.fixture("users").then((user) => {
        cy.pciLogin(user.admin);
      });
    });

    it("Should show page user/", () => {
      cy.visit(site_url + "user/");
      cy.contains(".pci-text-title", "Your reviews").should("exist");
    });

    it("Should show page recommender/", () => {
      cy.fixture("users").then((user) => {
        cy.pciLogin(user.recommender);
      });
      cy.visit(site_url + "recommender/");
      cy.contains(".pci-text-title", "Requests to handle a preprint").should("exist");
    });

    it("Should show page manager/", () => {
      cy.fixture("users").then((user) => {
        cy.pciLogin(user.manager);
      });
      cy.visit(site_url + "manager/");
      cy.contains(".pci-text-title", "Pending validations").should("exist");
    });

    it("Should show page admin/", () => {
      cy.visit(site_url + "admin/");
      cy.contains(".pci-text-title", "Users & roles").should("exist");
    });

    it("Should show page public/", () => {
      cy.visit(site_url + "public/");
      cy.contains(".pci-text-title", /'s profile$/).should("exist");
    });

  });

});
