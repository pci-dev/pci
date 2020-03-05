describe("Preprint post", () => {
  const articleTitle = "articleTest" + new Date().toLocaleString();
  const recommTitle = "recommendationTest" + new Date().toLocaleString();

  let submitter;
  let manager;
  let recommender;
  let reviewer_2;
  let reviewer_1;

  before(() => {
    //
    // cy.visit("http://127.0.0.1:8000/pcidev/");

    cy.fixture("users").then(user => {
      submitter = user.normal_user;
      manager = user.manager;
      recommender = user.recommender;
      reviewer_1 = user.co_recommender;
      reviewer_2 = user.developper;
    });
  });

  beforeEach(() => {
    Cypress.Cookies.preserveOnce(
      "session_id_admin",
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

    it("Should have a disclaimer", () => {
      cy.contains(".btn-success", "Submit a preprint").click();

      cy.contains(".btn-success", "Submit your preprint").should("exist");
      cy.contains(".btn-success", "Submit your preprint").click();
    });

    it("Should send submission form", () => {
      cy.fixture("fake_datas").then(datas => {
        cy.get("#t_articles_title").type("Tototototototot totoo");
        cy.get("#t_articles_authors").type(
          submitter.firstname + " " + submitter.lastname
        );
        cy.get("#t_articles_doi").type(datas.url);
        cy.get("#t_articles_abstract").type("Abstract " + datas.long_text, { delay: 0 });
        cy.get("#t_articles_keywords").type(datas.small_text);
        cy.get("#t_articles_cover_letter").type("Cover " + datas.long_text, { delay: 0 });
      });

      cy.get('input[name="thematics"]')
        .first()
        .click();

      cy.get("#t_articles_i_am_an_author").click();
      cy.get("#t_articles_is_not_reviewed_elsewhere").click();

      cy.get("input[type=submit]").click();

      cy.wait(500);
      cy.contains(".w2p_flash", "Article submitted").should("exist");
    });

    it("Should search for suggested recommender with no result", () => {
      cy.contains("a", "Suggest recommenders").click();

      // search nonsense string to expect no result
      cy.get('input[name="qyKeywords"]').type("zuklshlkjehrlkjaherlkjahr");
      cy.get(".pci2-search-button").click();

      cy.contains("a", "Suggest as recommender").should("not.exist");
    });

    it("Should use search to suggest recommender", () => {
      cy.get('input[name="qyKeywords"]').clear();

      cy.get('input[name="qyKeywords"]').type(recommender.firstname);
      cy.get(".pci2-search-button").click();
      cy.contains("a", "Suggest as recommender").should("exist");

      cy.contains("a", "Suggest as recommender").click();

      cy.wait(500);
      cy.contains(".w2p_flash", "Suggested recommender").should("exist");

      cy.contains("a", "Done").click();
    });

    it("Should have a suggested recommender", () => {
      cy.contains("li>span", recommender.firstname).should("exist");
      cy.contains("a", "Remove").should("exist");
    });

    it("Should complete submission and have 'SUBMISSION PENDING VALIDATION' status", () => {
      cy.contains("a", "Complete your submission").click();

      cy.get(".pci-status")
        .first()
        .should("contain", "SUBMISSION PENDING VALIDATION");
    });

    it("Should be able to edit article before managing board validation", () => {
      cy.contains("a", "View / Edit")
        .first()
        .click();

      cy.contains("a", "Edit article").click();

      cy.get("#t_articles_title").clear();

      cy.get("#t_articles_title").type(articleTitle);

      cy.get("input[type=submit]").click();

      cy.contains("h3", articleTitle).should("exist");
    });
  });

  //######################################################################################################################################
  describe("Manager : Preprint submission validation", () => {
    before(() => {
      // log as manager
      cy.pciLogin(manager);
    });

    it("Should have 'Pending validations' enhanced menu", () => {
      cy.contains(".pci-enhancedMenuItem", "Manage").should("exist");
      cy.contains(".dropdown-toggle", "Manage").click();

      cy.contains(".pci-enhancedMenuItem", "Pending validation").should(
        "exist"
      );
      cy.contains("a", "Pending validation").click();
    });

    it("Should show article in 'Pending validations' page", () => {
      cy.contains("tr", articleTitle).should("exist");

      cy.get(".pci-status")
        .first()
        .should("contain", "SUBMISSION PENDING VALIDATION");
    });

    it("Should validate submission", () => {
      cy.contains("a", "Check & Edit")
        .first()
        .click();

      cy.contains(".btn-success", "Validate this submission").should("exist");
      cy.contains(".btn-success", "Validate this submission").click();

      cy.wait(500);
      cy.contains(".w2p_flash", "Request now available to recommenders").should(
        "exist"
      );
    });

    it("Should article have status 'PREPRINT REQUIRING A RECOMMENDER'", () => {
      cy.contains(".pci-status-big", "PREPRINT REQUIRING A RECOMMENDER").should(
        "exist"
      );

      cy.contains(".dropdown-toggle", "Manage").click();
      cy.contains("a", "All article").click();

      cy.contains("tr", articleTitle).should("exist");
      cy.contains(".pci-status", "PREPRINT REQUIRING A RECOMMENDER")
        .first()
        .should("exist");
    });

    it("Should NOT show article in 'Pending validations' page", () => {
      cy.contains(".dropdown-toggle", "Manage").click();
      cy.contains("a", "Pending validation").click();

      cy.contains("tr", articleTitle).should("not.exist");
    });
  });

  //######################################################################################################################################
  describe("=> Verify article status : PREPRINT REQUIRING A RECOMMENDER", () => {
    it("=> submitter : article correct status", () => {
      cy.pciCheckArticleStatus(
        submitter,
        "submitter",
        "PREPRINT REQUIRING A RECOMMENDER",
        articleTitle
      );
    });

    it("=> manager : article correct status", () => {
      cy.pciCheckArticleStatus(
        manager,
        "manager",
        "PREPRINT REQUIRING A RECOMMENDER",
        articleTitle
      );
    });

    it("=> recommender : article correct status", () => {
      cy.pciCheckArticleStatus(
        recommender,
        "suggested_recommender",
        "PREPRINT REQUIRING A RECOMMENDER",
        articleTitle
      );
    });
  });

  //######################################################################################################################################
  describe("Recommender : Accept to recommend and invite reviewers", () => {
    before(() => {
      // log as normal_user

      cy.pciLogin(recommender);
    });

    it("Should have 'Request to handle a preprint' enhanced menu", () => {
      cy.contains(".pci-enhancedMenuItem", "Your Recommendations").should(
        "exist"
      );
      cy.contains(".dropdown-toggle", "Your Recommendations").click();

      cy.contains(
        ".pci-enhancedMenuItem",
        "requests to handle a preprint"
      ).should("exist");
      cy.contains("a", "requests to handle a preprint").click();
    });

    it("Should show article in 'Request to handle a preprint' page", () => {
      cy.contains("tr", articleTitle).should("exist");

      cy.get(".pci-status")
        .first()
        .should("contain", "PREPRINT REQUIRING A RECOMMENDER");
    });

    it("Should accept to recommend", () => {
      cy.contains("a", "View")
        .first()
        .click();

      cy.get(".btn-success.pci-recommender").should("exist");
      cy.get(".btn-success.pci-recommender").click();

      cy.get("input[type=submit]").should("have.attr", "disabled");

      cy.get("input[type=checkbox]").each($el => {
        $el.click();
      });

      cy.get("input[type=submit]").should("not.have.attr", "disabled");
      cy.get("input[type=submit]").click();

      cy.wait(500);
      cy.contains(".w2p_flash", "email sent to manager").should("exist");
      cy.contains(".w2p_flash", "email sent to submitter").should("exist");
      cy.contains(
        ".w2p_flash",
        "email sent to " + recommender.firstname
      ).should("exist");
    });

    it("Should search for reviewer 1 (co_recommender user)", () => {
      cy.contains(
        ".btn",
        "Choose a reviewer from PCI Evol Biol DEV database"
      ).click();

      cy.get('input[name="qyKeywords"]').type(reviewer_1.firstname);
      cy.get(".pci2-search-button").click();

      cy.contains("a", "Add").should("exist");
    });

    it("Should invite reviewer 1", () => {
      cy.contains("a", "Add").click();

      cy.get("input[type=submit]").click();

      cy.wait(500);
      cy.contains(
        ".w2p_flash",
        'email sent to "' + reviewer_1.firstname
      ).should("exist");
    });

    it("Should search for reviewer 2 (developper user)", () => {
      cy.contains(
        ".btn",
        "Choose a reviewer from PCI Evol Biol DEV database"
      ).click();

      cy.get('input[name="qyKeywords"]').type(reviewer_2.firstname);
      cy.get(".pci2-search-button").click();

      cy.contains("a", "Add").should("exist");
    });

    it("Should invite reviewer 2", () => {
      cy.contains("a", "Add").click();

      cy.get("input[type=submit]").click();

      cy.wait(500);
      cy.contains(
        ".w2p_flash",
        'email sent to "' + reviewer_2.firstname
      ).should("exist");
    });

    it("Should invite reviewer outside PCI database", () => {
      cy.contains(
        ".btn",
        "Choose a reviewer outside PCI Evol Biol DEV database"
      ).click();

      cy.get("#no_table_reviewer_first_name").type("Titi");
      cy.get("#no_table_reviewer_last_name").type("Toto");
      cy.get("#no_table_reviewer_email").type("ratalatapouet@toto.com");

      cy.get("input[type=submit]").click();

      cy.wait(500);
      cy.contains(".w2p_flash", 'email sent to "Titi Toto"').should("exist");
    });

    it("Should show article under status 'RECOMMENDATION PROCESS UNDERWAY'", () => {
      cy.contains("a", "Done").click();

      cy.contains("tr", articleTitle).should("exist");

      cy.get(".pci-status")
        .first()
        .should("contain", "RECOMMENDATION PROCESS UNDERWAY");
    });
  });

  //######################################################################################################################################
  describe("=> Verify article status : RECOMMENDATION PROCESS UNDERWAY", () => {
    it("=> submitter : article correct status", () => {
      cy.pciCheckArticleStatus(
        submitter,
        "submitter",
        "RECOMMENDATION PROCESS UNDERWAY",
        articleTitle
      );
    });

    it("=> manager : article correct status", () => {
      cy.pciCheckArticleStatus(
        manager,
        "manager",
        "RECOMMENDATION PROCESS UNDERWAY",
        articleTitle
      );
    });

    it("=> reviewer 1 : article correct status", () => {
      cy.pciCheckArticleStatus(
        reviewer_1,
        "suggested_reviewer",
        "RECOMMENDATION PROCESS UNDERWAY",
        articleTitle
      );
    });

    it("=> reviewer 2 : article correct status", () => {
      cy.pciCheckArticleStatus(
        reviewer_2,
        "suggested_reviewer",
        "RECOMMENDATION PROCESS UNDERWAY",
        articleTitle
      );
    });
  });

  //######################################################################################################################################
  describe("Reviewer 1 : Accept and submit review", () => {
    before(() => {
      // log as normal_user

      cy.pciLogin(reviewer_1);
    });

    it("Should have 'Request to handle a preprint' enhanced menu", () => {
      cy.contains(".pci-enhancedMenuItem", "Your contributions").should(
        "exist"
      );
      cy.contains(".dropdown-toggle", "Your contributions").click();

      cy.contains(
        ".pci-enhancedMenuItem",
        "invitations to review a preprint"
      ).should("exist");
      cy.contains("a", "invitations to review a preprint").click();
    });

    it("Should show article in 'Invitations to review a preprint' page", () => {
      cy.contains("tr", articleTitle).should("exist");

      cy.get(".pci-status")
        .first()
        .should("contain", "RECOMMENDATION PROCESS UNDERWAY");
    });

    it("Should accept to review article", () => {
      cy.contains("a", "Accept or decline")
        .first()
        .click();

      cy.contains("a", "Yes, I agree to review this preprint").click();

      cy.get("input[type=submit]").should("have.attr", "disabled");

      cy.get("input[type=checkbox]").each($el => {
        $el.click();
      });

      cy.get("input[type=submit]").should("not.have.attr", "disabled");
      cy.get("input[type=submit]").click();
    });

    it("=> mail sent to recommender and current reviewer", () => {
      cy.wait(500);
      cy.contains(
        ".w2p_flash",
        "email sent to " + recommender.firstname
      ).should("exist");
      cy.contains(".w2p_flash", "email sent to " + reviewer_1.firstname).should(
        "exist"
      );
    });

    it("Should write and submit review", () => {
      cy.contains("a", "Write, edit or upload your review").should("exist");
      cy.contains("a", "Write, edit or upload your review").click();

      cy.fixture("fake_datas").then(datas => {
        cy.get("#t_reviews_review").type("Review 1 " + datas.long_text);
      });

      cy.get('input[name="terminate"]').click();
    });

    it("=> mail sent to recommender and current reviewer", () => {
      cy.wait(500);
      cy.contains(
        ".w2p_flash",
        "email sent to " + recommender.firstname
      ).should("exist");
      cy.contains(".w2p_flash", "email sent to " + reviewer_1.firstname).should(
        "exist"
      );
    });

    it("Should have 'Request to handle a preprint' enhanced menu", () => {
      cy.contains(".dropdown-toggle", "Your contributions").click();
      cy.contains("a", "Your reviews").click();

      cy.get(".cyp-review-state")
        .first()
        .should("contain", "COMPLETED");

      cy.contains("a", "View / Edit")
        .first()
        .click();

      cy.contains("a", "Write, edit or upload your review").should("not.exist");
    });
  });

  //######################################################################################################################################
  describe("Reviewer 2 : Accept and submit review", () => {
    before(() => {
      // log as normal_user

      cy.pciLogin(reviewer_2);
    });

    it("Should have 'Request to handle a preprint' enhanced menu", () => {
      cy.contains(".pci-enhancedMenuItem", "Your contributions").should(
        "exist"
      );
      cy.contains(".dropdown-toggle", "Your contributions").click();

      cy.contains(
        ".pci-enhancedMenuItem",
        "invitations to review a preprint"
      ).should("exist");
      cy.contains("a", "invitations to review a preprint").click();
    });

    it("Should show article in 'Invitations to review a preprint' page", () => {
      cy.contains("tr", articleTitle).should("exist");

      cy.get(".pci-status")
        .first()
        .should("contain", "RECOMMENDATION PROCESS UNDERWAY");
    });

    it("Should accept to review article", () => {
      cy.contains("a", "Accept or decline")
        .first()
        .click();

      cy.contains("a", "Yes, I agree to review this preprint").click();

      cy.get("input[type=submit]").should("have.attr", "disabled");

      cy.get("input[type=checkbox]").each($el => {
        $el.click();
      });

      cy.get("input[type=submit]").should("not.have.attr", "disabled");
      cy.get("input[type=submit]").click();
    });

    it("=> mail sent to recommender and current reviewer", () => {
      cy.wait(500);
      cy.contains(
        ".w2p_flash",
        "email sent to " + recommender.firstname
      ).should("exist");
      cy.contains(".w2p_flash", "email sent to " + reviewer_2.firstname).should(
        "exist"
      );
    });

    it("Should write and submit review", () => {
      cy.contains("a", "Write, edit or upload your review").should("exist");
      cy.contains("a", "Write, edit or upload your review").click();

      cy.fixture("fake_datas").then(datas => {
        cy.get("#t_reviews_review").type("Review 2 " + datas.long_text);
      });

      cy.get('input[name="terminate"]').click();
    });

    it("=> mail sent to recommender and current reviewer", () => {
      cy.wait(500);
      cy.contains(
        ".w2p_flash",
        "email sent to " + recommender.firstname
      ).should("exist");
      cy.contains(".w2p_flash", "email sent to " + reviewer_2.firstname).should(
        "exist"
      );
    });

    it("Should have 'Request to handle a preprint' enhanced menu", () => {
      cy.contains(".dropdown-toggle", "Your contributions").click();
      cy.contains("a", "Your reviews").click();

      cy.get(".cyp-review-state")
        .first()
        .should("contain", "COMPLETED");

      cy.contains("a", "View / Edit")
        .first()
        .click();

      cy.contains("a", "Write, edit or upload your review").should("not.exist");
    });
  });

  //######################################################################################################################################
  describe("Recommender : Write recommendation decision => Need revision ", () => {
    before(() => {
      // log as normal_user

      cy.pciLogin(recommender);
    });

    it("Should have 'Your recommendations of preprints' enhanced menu", () => {
      cy.contains(".pci-enhancedMenuItem", "Your Recommendations").should(
        "exist"
      );
      cy.contains(".dropdown-toggle", "Your Recommendations").click();

      cy.contains(
        ".pci-enhancedMenuItem",
        "Your recommendations of preprints"
      ).should("exist");
      cy.contains("a", "Your recommendations of preprints").click();
    });

    it("Should show article in 'Your recommendations of preprints' page", () => {
      cy.contains("tr", articleTitle).should("exist");

      cy.get(".pci-status")
        .first()
        .should("contain", "RECOMMENDATION PROCESS UNDERWAY");
    });

    it("Should write recommendation decision", () => {
      cy.contains("a", "Check & Edit")
        .first()
        .click();

      cy.contains("a", "Write or edit your decision / recommendation").click();

      cy.get("#opinion_revise").click();

      cy.fixture("fake_datas").then(datas => {
        cy.get("#t_recommendations_recommendation_title").type(recommTitle);
        cy.get("#t_recommendations_recommendation_comments").type(
          "Final recomm " + datas.long_text
        );
      });

      cy.get('input[name="terminate"]').click();
    });

    it("=> mail sent to manager and recommender", () => {
      cy.wait(500);
      cy.contains(".w2p_flash", "Recommendation saved and completed");
      cy.contains(".w2p_flash", "email sent to manager").should("exist");
      cy.contains(
        ".w2p_flash",
        "email sent to " + recommender.firstname
      ).should("exist");
    });

    it("Should show article under status 'REQUEST OF REVISION PENDING VALIDATION'", () => {
      cy.contains("tr", articleTitle).should("exist");

      cy.get(".pci-status")
        .first()
        .should("contain", "REQUEST OF REVISION PENDING VALIDATION");
    });
  });

  //######################################################################################################################################
  describe("=> Verify article status : REQUEST OF REVISION PENDING VALIDATION", () => {
    it("=> submitter : article correct status", () => {
      cy.pciCheckArticleStatus(
        submitter,
        "submitter",
        "RECOMMENDATION PROCESS UNDERWAY",
        articleTitle
      );
    });

    it("=> manager : article correct status", () => {
      cy.pciCheckArticleStatus(
        manager,
        "manager",
        "REQUEST OF REVISION PENDING VALIDATION",
        articleTitle
      );
    });

    it("=> reviewer 1 : article correct status", () => {
      cy.pciCheckArticleStatus(
        reviewer_1,
        "reviewer",
        "RECOMMENDATION PROCESS UNDERWAY",
        articleTitle
      );
    });

    it("=> reviewer 2 : article correct status", () => {
      cy.pciCheckArticleStatus(
        reviewer_2,
        "reviewer",
        "RECOMMENDATION PROCESS UNDERWAY",
        articleTitle
      );
    });
  });

  //##################################################################################################################################
  describe("Manager : Validate recommendation decistion", () => {
    before(() => {
      // log as manager

      cy.pciLogin(manager);
    });

    it("Should have 'Pending validations' enhanced menu", () => {
      cy.contains(".pci-enhancedMenuItem", "Manage").should("exist");
      cy.contains(".dropdown-toggle", "Manage").click();

      cy.contains(".pci-enhancedMenuItem", "Pending validation").should(
        "exist"
      );
      cy.contains("a", "Pending validation").click();
    });

    it("Should show article in 'Pending validations' page", () => {
      cy.contains("tr", articleTitle).should("exist");

      cy.get(".pci-status")
        .first()
        .should("contain", "REQUEST OF REVISION PENDING VALIDATION");
    });

    it("Should validate the decision", () => {
      cy.contains("a", "Check & Edit")
        .first()
        .click();

      cy.contains("a", "Validate this decision").should("exist");
      cy.contains("a", "Validate this decision").click();
    });

    it("=> mail sent to all involved", () => {
      cy.wait(500);
      cy.contains(".w2p_flash", "email sent to manager " + manager.mail).should(
        "exist"
      );
      cy.contains(
        ".w2p_flash",
        "email sent to " + recommender.firstname
      ).should("exist");
      cy.contains(".w2p_flash", "email sent to " + reviewer_1.firstname).should(
        "exist"
      );
      cy.contains(".w2p_flash", "email sent to " + reviewer_2.firstname).should(
        "exist"
      );
      cy.contains(
        ".w2p_flash",
        "email sent to submitter " + submitter.firstname
      ).should("exist");
    });
  });

  //##################################################################################################################################
  describe("=> Verify article status : RECOMMENDATION PROCESS UNDERWAY", () => {
    it("=> submitter : article correct status", () => {
      cy.pciCheckArticleStatus(
        submitter,
        "submitter",
        "AWAITING REVISION",
        articleTitle
      );
    });

    it("=> recommender : article correct status", () => {
      cy.pciCheckArticleStatus(
        recommender,
        "recommender",
        "AWAITING REVISION",
        articleTitle
      );
    });

    it("=> reviewer 1 : article correct status", () => {
      cy.pciCheckArticleStatus(
        reviewer_1,
        "reviewer",
        "AWAITING REVISION",
        articleTitle
      );
    });

    it("=> reviewer 2 : article correct status", () => {
      cy.pciCheckArticleStatus(
        reviewer_2,
        "reviewer",
        "AWAITING REVISION",
        articleTitle
      );
    });
  });

  //##################################################################################################################################
  describe("Submitter : Submit author's reply for round 1", () => {
    before(() => {
      // log as normal_user
      cy.pciLogin(submitter);
    });

    it("Should have 'Your submitted preprint' enhanced menu", () => {
      cy.contains(".pci-enhancedMenuItem", "Your contributions").should(
        "exist"
      );
      cy.contains(".dropdown-toggle", "Your contributions").click();

      cy.contains(".pci-enhancedMenuItem", "Your submitted preprint").should(
        "exist"
      );
      cy.contains("a", "Your submitted preprint").click();
    });

    it("Should show article in 'Pending validations' page", () => {
      cy.contains("tr", articleTitle).should("exist");

      cy.get(".pci-status")
        .first()
        .should("contain", "AWAITING REVISION");
    });

    it("Should write and submit author's reply", () => {
      cy.contains("a", "View / Edit")
        .first()
        .click();

      cy.contains(
        "a",
        "Write, edit or upload your reply to the recommender"
      ).click();

      cy.fixture("fake_datas").then(datas => {
        cy.get("#t_recommendations_reply").type(
          "Author's reply " + datas.long_text
        );
      });

      cy.get('button[name="completed"]').click();
    });

    it("=> mail sent to manager and recommender", () => {
      cy.wait(500);
      cy.contains(".w2p_flash", "email sent to manager").should("exist");
      cy.contains(
        ".w2p_flash",
        "email sent to " + recommender.firstname
      ).should("exist");
    });
  });


  //##################################################################################################################################
  //# ROUND 2
  //##################################################################################################################################
  describe("ROUND 2 - Recommender : Re-invite reviewers", () => {
    before(() => {
      // log as normal_user

      cy.pciLogin(recommender);
    });

    it("Should have 'Your recommendations of preprints' enhanced menu", () => {
      cy.contains(".pci-enhancedMenuItem", "Your Recommendations").should(
        "exist"
      );
      cy.contains(".dropdown-toggle", "Your Recommendations").click();

      cy.contains(
        ".pci-enhancedMenuItem",
        "Your recommendations of preprints"
      ).should("exist");
      cy.contains("a", "Your recommendations of preprints").click();
    });

    it("Should show article in 'Your recommendations of preprints' page", () => {
      cy.contains("tr", articleTitle).should("exist");

      cy.get(".pci-status")
        .first()
        .should("contain", "RECOMMENDATION PROCESS UNDERWAY");

      cy.contains("a", "Invite a reviewer")
        .first()
        .click();
    });

    it("Should search for reviewer 1 (co_recommender user)", () => {
      cy.contains(
        ".btn",
        "Choose a reviewer from PCI Evol Biol DEV database"
      ).click();

      cy.get('input[name="qyKeywords"]').type(reviewer_1.firstname);
      cy.get(".pci2-search-button").click();

      cy.contains("a", "Add").should("exist");
    });

    it("Should invite reviewer 1", () => {
      cy.contains("a", "Add").click();

      cy.get("input[type=submit]").click();

      cy.wait(500);
      cy.contains(
        ".w2p_flash",
        'email sent to "' + reviewer_1.firstname
      ).should("exist");
    });

    it("Should search for reviewer 2 (developper user)", () => {
      cy.contains(
        ".btn",
        "Choose a reviewer from PCI Evol Biol DEV database"
      ).click();

      cy.get('input[name="qyKeywords"]').type(reviewer_2.firstname);
      cy.get(".pci2-search-button").click();

      cy.contains("a", "Add").should("exist");
    });

    it("Should invite reviewer 2", () => {
      cy.contains("a", "Add").click();

      cy.get("input[type=submit]").click();

      cy.wait(500);
      cy.contains(
        ".w2p_flash",
        'email sent to "' + reviewer_2.firstname
      ).should("exist");
    });

    it("Should show article under status 'RECOMMENDATION PROCESS UNDERWAY'", () => {
      cy.contains("a", "Done").click();

      cy.contains("tr", articleTitle).should("exist");

      cy.get(".pci-status")
        .first()
        .should("contain", "RECOMMENDATION PROCESS UNDERWAY");
    });
  });

  //######################################################################################################################################
  describe("=> Verify article status : RECOMMENDATION PROCESS UNDERWAY", () => {
    it("=> submitter : article correct status", () => {
      cy.pciCheckArticleStatus(
        submitter,
        "submitter",
        "RECOMMENDATION PROCESS UNDERWAY",
        articleTitle
      );
    });

    it("=> manager : article correct status", () => {
      cy.pciCheckArticleStatus(
        manager,
        "manager",
        "RECOMMENDATION PROCESS UNDERWAY",
        articleTitle
      );
    });

    it("=> reviewer 1 : article correct status", () => {
      cy.pciCheckArticleStatus(
        reviewer_1,
        "suggested_reviewer",
        "RECOMMENDATION PROCESS UNDERWAY",
        articleTitle
      );
    });

    it("=> reviewer 2 : article correct status", () => {
      cy.pciCheckArticleStatus(
        reviewer_2,
        "suggested_reviewer",
        "RECOMMENDATION PROCESS UNDERWAY",
        articleTitle
      );
    });
  });

  //######################################################################################################################################
  describe("ROUND 2 - Reviewer 1 : Accept and submit review", () => {
    before(() => {
      // log as normal_user

      cy.pciLogin(reviewer_1);
    });

    it("Should have 'Request to handle a preprint' enhanced menu", () => {
      cy.contains(".pci-enhancedMenuItem", "Your contributions").should(
        "exist"
      );
      cy.contains(".dropdown-toggle", "Your contributions").click();

      cy.contains(
        ".pci-enhancedMenuItem",
        "invitations to review a preprint"
      ).should("exist");
      cy.contains("a", "invitations to review a preprint").click();
    });

    it("Should show article in 'Invitations to review a preprint' page", () => {
      cy.contains("tr", articleTitle).should("exist");

      cy.get(".pci-status")
        .first()
        .should("contain", "RECOMMENDATION PROCESS UNDERWAY");
    });

    it("Should accept to review article", () => {
      cy.contains("a", "Accept or decline")
        .first()
        .click();

      cy.contains("a", "Yes, I agree to review this preprint").click();

      cy.get("input[type=submit]").should("have.attr", "disabled");

      cy.get("input[type=checkbox]").each($el => {
        $el.click();
      });

      cy.get("input[type=submit]").should("not.have.attr", "disabled");
      cy.get("input[type=submit]").click();
    });

    it("=> mail sent to recommender and current reviewer", () => {
      cy.wait(500);
      cy.contains(
        ".w2p_flash",
        "email sent to " + recommender.firstname
      ).should("exist");
      cy.contains(".w2p_flash", "email sent to " + reviewer_1.firstname).should(
        "exist"
      );
    });

    it("Should write and submit review", () => {
      cy.contains("a", "Write, edit or upload your review").should("exist");
      cy.contains("a", "Write, edit or upload your review").click();

      cy.fixture("fake_datas").then(datas => {
        cy.get("#t_reviews_review").type("Review 1 " + datas.long_text);
      });

      cy.get('input[name="terminate"]').click();
    });

    it("=> mail sent to recommender and current reviewer", () => {
      cy.wait(500);
      cy.contains(
        ".w2p_flash",
        "email sent to " + recommender.firstname
      ).should("exist");
      cy.contains(".w2p_flash", "email sent to " + reviewer_1.firstname).should(
        "exist"
      );
    });

    it("Should have 'Request to handle a preprint' enhanced menu", () => {
      cy.contains(".dropdown-toggle", "Your contributions").click();
      cy.contains("a", "Your reviews").click();

      cy.get(".cyp-review-state")
        .first()
        .should("contain", "COMPLETED");

      cy.contains("a", "View / Edit")
        .first()
        .click();

      cy.contains("a", "Write, edit or upload your review").should("not.exist");
    });
  });

  //######################################################################################################################################
  describe("ROUND 2 - Reviewer 2 : Accept and submit review", () => {
    before(() => {
      // log as normal_user

      cy.pciLogin(reviewer_2);
    });

    it("Should have 'Request to handle a preprint' enhanced menu", () => {
      cy.contains(".pci-enhancedMenuItem", "Your contributions").should(
        "exist"
      );
      cy.contains(".dropdown-toggle", "Your contributions").click();

      cy.contains(
        ".pci-enhancedMenuItem",
        "invitations to review a preprint"
      ).should("exist");
      cy.contains("a", "invitations to review a preprint").click();
    });

    it("Should show article in 'Invitations to review a preprint' page", () => {
      cy.contains("tr", articleTitle).should("exist");

      cy.get(".pci-status")
        .first()
        .should("contain", "RECOMMENDATION PROCESS UNDERWAY");
    });

    it("Should accept to review article", () => {
      cy.contains("a", "Accept or decline")
        .first()
        .click();

      cy.contains("a", "Yes, I agree to review this preprint").click();

      cy.get("input[type=submit]").should("have.attr", "disabled");

      cy.get("input[type=checkbox]").each($el => {
        $el.click();
      });

      cy.get("input[type=submit]").should("not.have.attr", "disabled");
      cy.get("input[type=submit]").click();
    });

    it("=> mail sent to recommender and current reviewer", () => {
      cy.wait(500);
      cy.contains(
        ".w2p_flash",
        "email sent to " + recommender.firstname
      ).should("exist");
      cy.contains(".w2p_flash", "email sent to " + reviewer_2.firstname).should(
        "exist"
      );
    });

    it("Should write and submit review", () => {
      cy.contains("a", "Write, edit or upload your review").should("exist");
      cy.contains("a", "Write, edit or upload your review").click();

      cy.fixture("fake_datas").then(datas => {
        cy.get("#t_reviews_review").type("Review 2 " + datas.long_text);
      });

      cy.get('input[name="terminate"]').click();
    });

    it("=> mail sent to recommender and current reviewer", () => {
      cy.wait(500);
      cy.contains(
        ".w2p_flash",
        "email sent to " + recommender.firstname
      ).should("exist");
      cy.contains(".w2p_flash", "email sent to " + reviewer_2.firstname).should(
        "exist"
      );
    });

    it("Should have 'Request to handle a preprint' enhanced menu", () => {
      cy.contains(".dropdown-toggle", "Your contributions").click();
      cy.contains("a", "Your reviews").click();

      cy.get(".cyp-review-state")
        .first()
        .should("contain", "COMPLETED");

      cy.contains("a", "View / Edit")
        .first()
        .click();

      cy.contains("a", "Write, edit or upload your review").should("not.exist");
    });
  });

  //######################################################################################################################################
  describe("ROUND 2 - Recommender : Write recommendation decision => Validation", () => {
    before(() => {
      // log as normal_user

      cy.pciLogin(recommender);
    });

    it("Should have 'Your recommendations of preprints' enhanced menu", () => {
      cy.contains(".pci-enhancedMenuItem", "Your Recommendations").should(
        "exist"
      );
      cy.contains(".dropdown-toggle", "Your Recommendations").click();

      cy.contains(
        ".pci-enhancedMenuItem",
        "Your recommendations of preprints"
      ).should("exist");
      cy.contains("a", "Your recommendations of preprints").click();
    });

    it("Should show article in 'Your recommendations of preprints' page", () => {
      cy.contains("tr", articleTitle).should("exist");

      cy.get(".pci-status")
        .first()
        .should("contain", "RECOMMENDATION PROCESS UNDERWAY");
    });

    it("Should write recommendation decision", () => {
      cy.contains("a", "Check & Edit")
        .first()
        .click();

      cy.contains("a", "Write or edit your decision / recommendation").click();

      cy.get("#opinion_recommend").click();

      cy.fixture("fake_datas").then(datas => {
        cy.get("#t_recommendations_recommendation_title").type(recommTitle);
        cy.get("#t_recommendations_recommendation_comments").type(
          "Recomm " + datas.long_text
        );
      });

      cy.get('input[name="terminate"]').click();
    });

    it("=> mail sent to manager and recommender", () => {
      cy.wait(500);
      cy.contains(".w2p_flash", "Recommendation saved and completed");
      cy.contains(".w2p_flash", "email sent to manager").should("exist");
      cy.contains(
        ".w2p_flash",
        "email sent to " + recommender.firstname
      ).should("exist");
    });

    it("Should show article under status 'RECOMMENDATION PENDING VALIDATION'", () => {
      cy.contains("tr", articleTitle).should("exist");

      cy.get(".pci-status")
        .first()
        .should("contain", "RECOMMENDATION PENDING VALIDATION");
    });
  });

  //######################################################################################################################################
  describe("=> Verify article status : RECOMMENDATION PENDING VALIDATION", () => {
    it("=> submitter : article correct status", () => {
      cy.pciCheckArticleStatus(
        submitter,
        "submitter",
        "RECOMMENDATION PROCESS UNDERWAY",
        articleTitle
      );
    });

    it("=> manager : article correct status", () => {
      cy.pciCheckArticleStatus(
        manager,
        "manager",
        "RECOMMENDATION PENDING VALIDATION",
        articleTitle
      );
    });

    it("=> reviewer 1 : article correct status", () => {
      cy.pciCheckArticleStatus(
        reviewer_1,
        "reviewer",
        "RECOMMENDATION PROCESS UNDERWAY",
        articleTitle
      );
    });

    it("=> reviewer 2 : article correct status", () => {
      cy.pciCheckArticleStatus(
        reviewer_2,
        "reviewer",
        "RECOMMENDATION PROCESS UNDERWAY",
        articleTitle
      );
    });
  });

  //##################################################################################################################################
  describe(" ROUND 2 - Manager : Validate recommendation", () => {
    before(() => {
      // log as manager

      cy.pciLogin(manager);
    });

    it("Should have 'Pending validations' enhanced menu", () => {
      cy.contains(".pci-enhancedMenuItem", "Manage").should("exist");
      cy.contains(".dropdown-toggle", "Manage").click();

      cy.contains(".pci-enhancedMenuItem", "Pending validation").should(
        "exist"
      );
      cy.contains("a", "Pending validation").click();
    });

    it("Should show article in 'Pending validations' page", () => {
      cy.contains("tr", articleTitle).should("exist");

      cy.get(".pci-status")
        .first()
        .should("contain", "RECOMMENDATION PENDING VALIDATION");
    });

    it("Should validate the recommendation", () => {
      cy.contains("a", "Check & Edit")
        .first()
        .click();

      cy.contains("a", "Validate this recommendation").should("exist");
      cy.contains("a", "Validate this recommendation").click();
    });

    it("=> mail sent to all involved", () => {
      cy.wait(500);
      cy.contains(".w2p_flash", "email sent to manager " + manager.mail).should(
        "exist"
      );
      cy.contains(
        ".w2p_flash",
        "email sent to " + recommender.firstname
      ).should("exist");
      cy.contains(".w2p_flash", "email sent to " + reviewer_1.firstname).should(
        "exist"
      );
      cy.contains(".w2p_flash", "email sent to " + reviewer_2.firstname).should(
        "exist"
      );
      cy.contains(
        ".w2p_flash",
        "email sent to submitter " + submitter.firstname
      ).should("exist");
    });
  });

  //##################################################################################################################################
  describe("=> Verify article status : RECOMMENDED", () => {
    it("=> submitter : article correct status", () => {
      cy.pciCheckArticleStatus(
        submitter,
        "submitter",
        "RECOMMENDED",
        articleTitle
      );
    });

    it("=> recommender : article correct status", () => {
      cy.pciCheckArticleStatus(
        recommender,
        "recommender",
        "RECOMMENDED",
        articleTitle
      );
    });

    it("=> reviewer 1 : article correct status", () => {
      cy.pciCheckArticleStatus(
        reviewer_1,
        "reviewer",
        "RECOMMENDED",
        articleTitle
      );
    });

    it("=> reviewer 2 : article correct status", () => {
      cy.pciCheckArticleStatus(
        reviewer_2,
        "reviewer",
        "RECOMMENDED",
        articleTitle
      );
    });
  });

  //##################################################################################################################################
  describe("Manager : Delete preprint", () => {
    it("Should delete article", () => {
      cy.pciDeleteWithTestLastArticle(articleTitle);
    });
  });

  //##################################################################################################################################
  describe("=> Verify article status : not exist", () => {
    it("=> submitter : article not exist", () => {
      cy.pciCheckArticleStatus(
        submitter,
        "submitter",
        "not.exist",
        articleTitle
      );
    });

    it("=> recommender : article not exist", () => {
      cy.pciCheckArticleStatus(
        recommender,
        "recommender",
        "not.exist",
        articleTitle
      );
    });

    it("=> manager : article not exist", () => {
      cy.pciCheckArticleStatus(manager, "manager", "not.exist", articleTitle);
    });

    it("=> reviewer 1 : article not exist", () => {
      cy.pciCheckArticleStatus(
        reviewer_1,
        "reviewer",
        "not.exist",
        articleTitle
      );
    });

    it("=> reviewer 2 : article not exist", () => {
      cy.pciCheckArticleStatus(
        reviewer_2,
        "reviewer",
        "not.exist",
        articleTitle
      );
    });
  });
});
