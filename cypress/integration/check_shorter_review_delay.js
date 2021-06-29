describe("Preprint recommended in one round", () => {
  const articleTitle = "articleTest" + new Date().toLocaleString();
  const recommTitle = "recommendationTest" + new Date().toLocaleString();
  const currentTest = "preprint_1_round_recommendation";

  let submitter;
  let manager;
  let recommender;
  let reviewer;

  before(() => {
    cy.fixture("users").then((user) => {
      submitter = user.normal_user;
      manager = user.manager;
      recommender = user.recommender;
      reviewer = user.developer;
    });
  });

  beforeEach(() => {
    Cypress.Cookies.preserveOnce(
      "session_id_admin",
      "session_id_pci",
      "session_id_pcidev",
      "session_id_welcome"
    );
  });

  //######################################################################################################################################
  describe("Submitter : Preprint submission", () => {
    before(() => {
      // log as normal_user

      cy.pciLogin(submitter);
    });

    it("Should show a disclaimer before submission", () => {
      cy.contains(".btn-success", "Submit a preprint").click();

      cy.contains(".btn-success", "Submit your preprint").should("exist");
      cy.contains(".btn-success", "Submit your preprint").click();
    });

    it("Should submit form with bad title", () => {
      cy.fixture("fake_datas").then((datas) => {
        cy.get("#t_articles_title_ifr").typeTinymce("Tototototototot totoo");
        cy.get("#t_articles_authors").typeFast(
          submitter.firstname + " " + submitter.lastname
        );
        cy.get("#t_articles_doi").typeFast(datas.doi);
        // cy.get("#t_articles_abstract").typeFast("Abstract " + datas.long_text);
        cy.get("#t_articles_abstract_ifr").typeTinymce(
          "Abstract " + datas.long_html_text
        );
        cy.get("#t_articles_keywords").typeFast(datas.small_text);
        // cy.get("#t_articles_cover_letter").typeFast("Cover " + datas.long_text);
        cy.get("#t_articles_cover_letter_ifr").typeTinymce(
          "Cover " + datas.long_html_text
        );
      });

      cy.get('input[name="thematics"]').first().click();

      cy.get("#t_articles_i_am_an_author").click();
      cy.get("#t_articles_is_not_reviewed_elsewhere").click();

      cy.get("input[type=submit]").click();

      cy.wait(500);
      cy.contains(".w2p_flash", "Article submitted").should("exist");
    });

    it("Should search for suggested recommender and have no result", () => {
      cy.contains("a", "Suggest recommenders").click();

      // search nonsense string to expect no result
      cy.get('input[name="qyKeywords"]').typeFast("zuklshlkjehrlkjaherlkjahr");
      cy.get(".pci2-search-button").click();

      cy.contains("a", "Suggest as recommender").should("not.exist");
    });

    it("Should search and suggest recommender", () => {
      cy.get('input[name="qyKeywords"]').clear();

      cy.get('input[name="qyKeywords"]').typeFast(recommender.firstname);
      cy.get(".pci2-search-button").click();
      cy.contains("a", "Suggest as recommender").should("exist");

      cy.contains("a", "Suggest as recommender").click();
    });

    it("=> mail sent to recommender", () => {
      cy.wait(500);
      cy.contains(".w2p_flash", "Suggested recommender").should("exist");
    });

    it("Should have a suggested recommender", () => {
      cy.contains("a", "Done").click();

      cy.contains("li>span", recommender.firstname).should("exist");
      cy.contains("a", "Remove").should("exist");
    });

    it("Should complete submission and have 'SUBMISSION PENDING VALIDATION' status", () => {
      cy.contains("a", "Complete your submission").click();

      cy.get(".pci-status")
        .first()
        .should("contain", "SUBMISSION PENDING VALIDATION");
    });

    it("Should be able to edit submission and set correct title before validation", () => {
      cy.contains("a", "View / Edit").first().click();

      cy.contains("a", "Edit article").click();

      cy.get("#t_articles_title_ifr").clearTinymce();

      cy.fixture("fake_datas").then((datas) => {
        cy.get("#t_articles_title_ifr").typeTinymce(
          articleTitle + " " + datas.small_text
        );
      });

      cy.get("input[type=submit]").click();

      cy.contains("h3", articleTitle).should("exist");
    });
  });

  describe("1 - Prepint submitted => check status : SUBMISSION PENDING VALIDATION", () => {
    it("=> submitter : article correct status", () => {
      cy.pciCheckArticleStatus(
        currentTest,
        submitter,
        "submitter",
        "1-Prepint submitted",
        "SUBMISSION PENDING VALIDATION",
        articleTitle
      );
    });

    it("=> manager : article correct status", () => {
      cy.pciCheckArticleStatus(
        currentTest,
        manager,
        "manager",
        "1-Prepint submitted",
        "SUBMISSION PENDING VALIDATION",
        articleTitle
      );
    });
  });

  //######################################################################################################################################
  describe("Manager : Preprint submission validation", () => {
    before(() => {
      // log as manager
      cy.pciLogin(manager);
    });

    it("Should show 'Pending validation(s)' enhanced menu", () => {
      cy.contains(".pci-enhancedMenuItem", "For managers").should("exist");
      cy.contains(".dropdown-toggle", "For managers").click();

      cy.contains(".pci-enhancedMenuItem", "Pending validation").should(
        "exist"
      );
      cy.contains("a", "Pending validation").click();
    });

    it("Should show article in 'Pending validation(s)' page", () => {
      cy.contains("tr", articleTitle).should("exist");

      cy.get(".pci-status")
        .first()
        .should("contain", "SUBMISSION PENDING VALIDATION");
    });

    it("Should validate the submission", () => {
      cy.contains("a", "View / Edit").first().click();

      cy.contains(".btn-success", "Validate this submission").should("exist");
      cy.contains(".btn-success", "Validate this submission").click();

      cy.wait(500);
      cy.contains(".w2p_flash", "Request now available to recommenders").should(
        "exist"
      );
    });

    it("Should article under status 'PREPRINT REQUIRING A RECOMMENDER'", () => {
      cy.contains(".pci-status-big", "PREPRINT REQUIRING A RECOMMENDER").should(
        "exist"
      );

      cy.contains(".dropdown-toggle", "For managers").click();
      cy.contains("a", "All article").click();

      cy.contains("tr", articleTitle).should("exist");
      cy.contains(".pci-status", "PREPRINT REQUIRING A RECOMMENDER")
        .first()
        .should("exist");
    });

    it("Should NOT show article in 'Pending validation(s)' page", () => {
      cy.contains(".dropdown-toggle", "For managers").click();
      cy.contains("a", "Pending validation").click();

      cy.contains("tr", articleTitle).should("not.exist");
    });
  });

  //######################################################################################################################################
  describe("2 - Submission validated => check status : PREPRINT REQUIRING A RECOMMENDER", () => {
    it("=> submitter : article correct status", () => {
      cy.pciCheckArticleStatus(
        currentTest,
        submitter,
        "submitter",
        "2-Submission validated",
        "PREPRINT REQUIRING A RECOMMENDER",
        articleTitle
      );
    });

    it("=> manager : article correct status", () => {
      cy.pciCheckArticleStatus(
        currentTest,
        manager,
        "manager",
        "2-Submission validated",
        "PREPRINT REQUIRING A RECOMMENDER",
        articleTitle
      );
    });

    it("=> recommender : article correct status", () => {
      cy.pciCheckArticleStatus(
        currentTest,
        recommender,
        "suggested_recommender",
        "2-Submission validated",
        "PREPRINT REQUIRING A RECOMMENDER",
        articleTitle
      );
    });
  });

  //######################################################################################################################################
  describe("Recommender :  Accept to recommend and invite reviewers", () => {
    before(() => {
      // log as normal_user

      cy.pciLogin(recommender);
    });

    it("Should show 'Request(s) to handle a preprint' enhanced menu", () => {
      cy.contains(".pci-enhancedMenuItem", "For recommenders").should("exist");
      cy.contains(".dropdown-toggle", "For recommenders").click();

      cy.contains(
        ".pci-enhancedMenuItem",
        "Request(s) to handle a preprint"
      ).should("exist");
      cy.contains("a", "Request(s) to handle a preprint").click();
    });

    it("Should show article in 'Request(s) to handle a preprint' page", () => {
      cy.contains("tr", articleTitle).should("exist");

      cy.get(".pci-status")
        .first()
        .should("contain", "PREPRINT REQUIRING A RECOMMENDER");
    });

    it("Should accept to recommend the preprint", () => {
      cy.contains("a", "View").first().click();

      cy.get(".btn-success.pci-recommender").should("exist");
      cy.get(".btn-success.pci-recommender").click();

      cy.get("input[type=submit]").should("have.attr", "disabled");

      cy.get("input[type=checkbox]").each(($el) => {
        $el.click();
      });

      cy.get("input[type=submit]").should("not.have.attr", "disabled");
      cy.get("input[type=submit]").click();
    });

    it("=> mail sent to manager, submitter and recommender", () => {
      cy.wait(500);
      cy.contains(".w2p_flash", "e-mail sent to manager").should("exist");
      cy.contains(".w2p_flash", "e-mail sent to submitter").should("exist");
      cy.contains(
        ".w2p_flash",
        "e-mail sent to " + recommender.firstname
      ).should("exist");
    });

    it("Should search for reviewer (developer user)", () => {
      cy.contains(
        ".btn",
        "Choose a reviewer from the PCI Evol Biol DEV database"
      ).click();

      cy.get('input[name="qyKeywords"]').typeFast(reviewer.firstname);
      cy.get(".pci2-search-button").click();

      cy.contains("a", "Prepare an invitation").should("exist");
    });

    it("Should invite reviewer", () => {
      cy.contains("a", "Prepare an invitation").click();

      cy.get("input[type=submit]").click();
    });

    it("=> mail sent to reviewer", () => {
      cy.wait(500);
      cy.contains(".w2p_flash", "e-mail sent to " + reviewer.firstname).should(
        "exist"
      );
    });

    it("Should show article under status 'HANDLING PROCESS UNDERWAY'", () => {
      cy.contains("a", "Done").click();
      cy.contains("tr", articleTitle).should("exist");

      // cy.get(".pci-status")
      //   .first()
      //   .should("contain", "HANDLING PROCESS UNDERWAY");
    });
  });

  //######################################################################################################################################
  describe("3 - Review invitations sent => check status : HANDLING PROCESS UNDERWAY", () => {
    it("=> submitter : article correct status", () => {
      cy.pciCheckArticleStatus(
        currentTest,
        submitter,
        "submitter",
        "3-Review invitations sent",
        "HANDLING PROCESS UNDERWAY",
        articleTitle
      );
    });

    it("=> manager : article correct status", () => {
      cy.pciCheckArticleStatus(
        currentTest,
        manager,
        "manager",
        "3-Review invitations sent",
        "HANDLING PROCESS UNDERWAY",
        articleTitle
      );
    });

    it("=> recommender : article correct status", () => {
      cy.pciCheckArticleStatus(
        currentTest,
        recommender,
        "recommender",
        "3-Review invitations sent",
        "HANDLING PROCESS UNDERWAY",
        articleTitle
      );
    });

    it("=> reviewer : article correct status", () => {
      cy.pciCheckArticleStatus(
        currentTest,
        reviewer,
        "suggested_reviewer",
        "3-Review invitations sent",
        "HANDLING PROCESS UNDERWAY",
        articleTitle
      );
    });

  });

  //######################################################################################################################################
  describe("Reviewer : Accept and submit review", () => {
    before(() => {
      // log as normal_user

      cy.pciLogin(reviewer);
    });

    it("Should show 'Request(s) to handle a preprint' enhanced menu", () => {
      cy.contains(".pci-enhancedMenuItem", "For contributors").should("exist");
      cy.contains(".dropdown-toggle", "For contributors").click();

      cy.contains(
        ".pci-enhancedMenuItem",
        "Invitation(s) to review a preprint"
      ).should("exist");
      cy.contains("a", "Invitation(s) to review a preprint").click();
    });

    it("Should show article in 'Invitation(s) to review a preprint' page", () => {
      cy.contains("tr", articleTitle).should("exist");

      cy.get(".pci-status")
        .first()
        .should("contain", "HANDLING PROCESS UNDERWAY");
    });

    it("Should accept to review article", () => {
      cy.contains("a", "Accept or decline").first().click();

      cy.contains("a", "Yes, I would like to review this preprint").click();

      cy.get("input[type=submit]").should("have.attr", "disabled");

      cy.get("input[type=checkbox]").each(($el) => {
        $el.click();
      });

      cy.get("input[type=submit]").should("not.have.attr", "disabled");
      cy.get("input[type=submit]").click();
    });

    it("=> mail sent to recommender and current reviewer", () => {
      cy.wait(500);
      cy.contains(
        ".w2p_flash",
        "e-mail sent to " + recommender.firstname
      ).should("exist");
      cy.contains(".w2p_flash", "e-mail sent to " + reviewer.firstname).should(
        "exist"
      );
    });
  });

});
