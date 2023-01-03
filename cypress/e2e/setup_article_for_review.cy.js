describe("Preprint recommendation setup for review", () => {
  const articleTitle = "articleTest" + new Date().toLocaleString();
  const recommTitle = "recommendationTest" + new Date().toLocaleString();

  let submitter;
  let manager;
  let admin;
  let recommender;
  let reviewer;
  let data;

  before(() => {
    cy.fixture("users").then((user) => {
      submitter = user.normal_user;
      manager = user.manager;
      admin = user.admin;
      recommender = user.recommender;
      reviewer = user.developer;
    });
    cy.fixture("fake_datas").then((_data) => {
      data = _data;
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
      cy.pciLogin(submitter);
    });

    it("Should initate the submission of a preprint", () => {
      cy.contains(".btn-success", "Submit a preprint").click({force: true});
      // button exists in DOM, but display: none in pci-timo.css => click {force: true}
      cy.contains(".btn-success", "Submit your preprint").click();
    });

    it("Should submit the submission form", () => {
      cy.get("#t_articles_title").typeFast(articleTitle);
      cy.get("#t_articles_authors").typeFast(submitter.firstname + " " + submitter.lastname);
      cy.get("#t_articles_doi").typeFast(data.doi);
      // cy.get("#t_articles_abstract").typeFast("Abstract " + data.long_text);
      cy.get("#t_articles_abstract_ifr").typeTinymce("Abstract " + data.long_html_text);
      cy.get("#t_articles_keywords").typeFast(data.small_text);
      // cy.get("#t_articles_cover_letter").typeFast("Cover " + data.long_text);
      cy.get("#t_articles_cover_letter_ifr").typeTinymce("Cover " + data.long_html_text);

      cy.get("#t_articles_no_results_based_on_data").click();
      cy.get("#t_articles_no_scripts_used_for_result").click();
      cy.get("#t_articles_codes_used_in_study").click();
      cy.get("#t_articles_codes_doi").typeFast("https://github.com/");

      cy.get('input[name="thematics"]').first().click();
      cy.get("#t_articles_i_am_an_author").click();
      cy.get("#t_articles_is_not_reviewed_elsewhere").click();
      cy.get("#t_articles_guide_read").click();
      cy.get("#t_articles_approvals_obtained").click();
      cy.get("#t_articles_human_subject_consent_obtained").click();
      cy.get("#t_articles_lines_numbered").click();
      cy.get("#t_articles_conflicts_of_interest_indicated").click();
      cy.get("#t_articles_no_financial_conflict_of_interest").click();
      cy.get("input[type=submit]").click();

      cy.wait(500);
      cy.contains(".w2p_flash", "Article submitted").should("exist");
    });

    it("Should search and suggest recommender", () => {
      cy.contains("a", "Suggest recommenders").click();
      cy.get('#simple-search-input').clear();
      cy.get('#simple-search-input').typeFast(recommender.firstname);
      //cy.get(".pci2-search-button").click(); // search button not shown (pci-timo.css), use enter
      cy.get('#simple-search-input').type("{enter}");
      cy.contains("a", "Suggest as recommender").should("exist");
      cy.contains("a", "Suggest as recommender").click();
    });

    it("=> mail sent to recommender", () => {
      cy.wait(500);
      cy.contains(".w2p_flash", "Suggested recommender").should("exist");
      cy.contains("a", "Done").click();
    });

    it("Should complete submission and have 'SUBMISSION PENDING VALIDATION' status", () => {
      cy.contains("a", "Complete your submission").click();

      cy.get(".pci-status")
        .first()
        .should("contain", "SUBMISSION PENDING VALIDATION");
    });
  });

  //######################################################################################################################################
  describe("Manager : Preprint submission validation", () => {
    before(() => {
      cy.pciLogin(manager);
    });

    it("Should show article in 'Pending validation(s)' page", () => {
      cy.contains(".dropdown-toggle", "For managers").click();
      cy.contains("a", "Pending validation").click();
      cy.contains("tr", articleTitle).should("exist");
      cy.contains(".pci-status", "SUBMISSION PENDING VALIDATION")
        .first()
        .should("exist");
    });

    it("Should validate the submission", () => {
      cy.contains("a", "View / Edit").first().click();
      cy.contains(".btn-success", "Validate this submission").click();

      cy.wait(500);
      cy.contains(".w2p_flash", "Request now available to recommenders").should("exist");
    });

    it("Should show article status 'PREPRINT REQUIRING A RECOMMENDER'", () => {
      cy.contains(".dropdown-toggle", "For managers").click();
      cy.contains("a", "All article").click();

      cy.contains("tr", articleTitle).should("exist");
      cy.contains(".pci-status", "PREPRINT REQUIRING A RECOMMENDER")
        .first()
        .should("exist");
    });

    it("Should no longer show article in 'Pending validation(s)' page", () => {
      cy.contains(".dropdown-toggle", "For managers").click();
      cy.contains("a", "Pending validation").click();

      cy.contains("tr", articleTitle).should("not.exist");
    });
  });

  //######################################################################################################################################
  describe("Recommender :  Accept to recommend and invite reviewers", () => {
    before(() => {
      cy.pciLogin(recommender);
    });

    it("Should show 'Request(s) to handle a preprint' enhanced menu", () => {
      cy.contains(".dropdown-toggle", "For recommenders").click();
      cy.contains("a", "Request(s) to handle a preprint").click();
    });

    it("Should show article in 'Request(s) to handle a preprint' page", () => {
      cy.contains("tr", articleTitle).should("exist");
      cy.contains(".pci-status", "PREPRINT REQUIRING A RECOMMENDER").should("exist");
    });

    it("Should accept to recommend the preprint", () => {
      cy.contains("a", "View").first().click();
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
      cy.contains(".w2p_flash", "e-mail sent to admin").should("exist");
      cy.contains(".w2p_flash", "e-mail sent to submitter").should("exist");
      cy.contains(".w2p_flash", "e-mail sent to " + recommender.firstname).should("exist");
    });

    it("Should search for reviewer (developer user)", () => {
      cy.contains(".btn", "Choose a reviewer from the PCI Evol Biol DEV database").click();

      cy.get('#simple-search-input').typeFast(reviewer.firstname);
      //cy.get(".pci2-search-button").click(); // search button not shown (pci-timo.css), use enter
      cy.get('#simple-search-input').type("{enter}");

      cy.contains("a", "Prepare an invitation").should("exist");
    });

    it("Should invite reviewer", () => {
      cy.contains("a", "Prepare an invitation").click();
      cy.get("input[type=submit]").click();
    });

    it("=> mail sent to reviewer", () => {
      cy.wait(500);
      cy.contains(".w2p_flash", "e-mail sent to " + reviewer.firstname).should("exist");
      cy.contains("a", "Done").click();
    });

    it("Should show article in list of articles", () => {
      cy.contains("tr", articleTitle).should("exist");
    });
  });


  describe("Recommender :  invite external un-registered reviewer", () => {
    before(() => {
      cy.pciLogin(recommender);
    });

    it("Should show article in recommender dashboard", () => {
      cy.contains(".dropdown-toggle", "For recommenders").click();
      cy.contains("a", "Preprint(s) you are handling").click();
      cy.contains(".doi_url", data.doi).should("exist");
    });

    it("Should invite reviewer outside PCI database", () => {
      cy.contains(".btn", "Invite a reviewer").first().click();
      cy.contains(".btn", "Choose a reviewer outside PCI Evol Biol DEV database").click();

      cy.get("#no_table_reviewer_first_name").typeFast("Titi");
      cy.get("#no_table_reviewer_last_name").typeFast("Toto");
      cy.get("#no_table_reviewer_email").typeFast("ratalatapouet@toto.com");

      cy.get("input[type=submit]").click();
    });

    it("=> mail sent to reviewer outside PCI db", () => {
      cy.wait(500);
      cy.contains(".w2p_flash", "e-mail sent to Titi Toto").should("exist");
    });
  });

/*
  //######################################################################################################################################
  describe("Reviewer : Accept and submit review", () => {
    before(() => {
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
*/

});
