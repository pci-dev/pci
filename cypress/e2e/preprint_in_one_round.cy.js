describe("Preprint recommended in one round", () => {
  const articleTitle = "articleTest" + new Date().toLocaleString();
  const recommTitle = "recommendationTest" + new Date().toLocaleString();
  const currentTest = "preprint_1_round_recommendation";

  const is_rr = false;

  let submitter;
  let manager;
  let admin;
  let recommender;
  let reviewer_2;
  let reviewer_1;

  before(() => {
    cy.fixture("users").then((user) => {
      submitter = user.normal_user;
      manager = user.manager;
      admin = user.admin;
      recommender = user.recommender;
      reviewer_1 = user.co_recommender;
      reviewer_2 = user.developer;
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
      cy.contains(".btn-success", "Submit a preprint").click({force: true});
      // button exists in DOM, but display: none in pci-timo.css => click {force: true}

      cy.contains(".btn-success", "Submit your preprint").should("exist");
      cy.contains(".btn-success", "Submit your preprint").click();
    });

    it("Should submit form with bad title", () => {
      cy.fixture("fake_datas").then((datas) => {
        cy.get("#t_articles_title").typeFast("Tototototototot totoo");
        cy.get("#t_articles_authors").typeFast(
          submitter.firstname + " " + submitter.lastname
        );
        cy.get("#t_articles_doi").typeFast(datas.doi);
        cy.get("#t_articles_abstract_ifr").typeTinymce(
          "Abstract " + datas.long_html_text
        );
        cy.get("#t_articles_keywords").typeFast(datas.small_text);
        cy.get("#t_articles_cover_letter_ifr").typeTinymce(
          "Cover " + datas.long_html_text
        );
      });

      var art_version = (is_rr ? "v1" : "1");
      cy.get("#t_articles_ms_version").typeFast(art_version);

      var art_year = new Date().getFullYear();
      cy.get("#t_articles_article_year").typeFast(art_year);

      cy.get("#t_articles_preprint_server").typeFast("Preprint server");

      if (is_rr) {
        cy.get("#t_articles_report_stage").send_keys("Stage 1");
        cy.get("#t_articles_sub_thematics").typeFast("sub-thematic");
      }

      if (!is_rr) {
      cy.get("#t_articles_uploaded_picture").selectFile("tests/image.png");
      cy.get("#t_articles_no_results_based_on_data").click();
      cy.get("#t_articles_no_scripts_used_for_result").click();
      cy.get("#t_articles_codes_used_in_study").click();
      cy.get("#t_articles_codes_doi").typeFast("https://github.com/");
      cy.get("#t_articles_funding").typeFast("The authors declare that they have received no specific funding for this study");
      }

      cy.get('input[name="thematics"]').first().click();

      cy.get("#t_articles_i_am_an_author").click();
      cy.get("#t_articles_is_not_reviewed_elsewhere").click();
      if (!is_rr) {
      cy.get("#t_articles_guide_read").click();
      cy.get("#t_articles_approvals_obtained").click();
      cy.get("#t_articles_human_subject_consent_obtained").click();
      cy.get("#t_articles_lines_numbered").click();
      cy.get("#t_articles_conflicts_of_interest_indicated").click();
      cy.get("#t_articles_no_financial_conflict_of_interest").click();
      }

      cy.get("input[type=submit]").click();

      if (is_rr) {
        fill_survey();
        gy.get("input[type=submit]").click();
      }

      cy.wait(500);
      cy.contains(".w2p_flash", "Article submitted").should("exist");
    });

    it("Should search for suggested recommender and have no result", () => {
      cy.contains("a", "Suggest recommenders").click();

      // search nonsense string to expect no result
      cy.get('#simple-search-input').typeFast("zuklshlkjehrlkjaherlkjahr");
      cy.get('#simple-search-input').type("{enter}");

      cy.contains("a", "Suggest as recommender").should("not.exist");
    });

    it("Should search and suggest recommender", () => {
      cy.get('#simple-search-input').clear();

      cy.get('#simple-search-input').typeFast(recommender.firstname);
      cy.get('#simple-search-input').type("{enter}");
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

      cy.get("#t_articles_title").clear();

      cy.fixture("fake_datas").then((datas) => {
        cy.get("#t_articles_title").typeFast(
          articleTitle + " " + datas.small_text
        );
      });

      cy.get("input[type=submit]").click();

      cy.contains("h4", "Confirm changes").should("exist");

      cy.get("button#bpt").click();

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
      if (!is_rr) {
      cy.get("#article_doi_correct").click();
      cy.get("#code_and_scripts_ok").click();
      cy.get("#scope_ok").click();
      cy.get("#data_ok").click();
      }
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
      cy.contains(".w2p_flash", "e-mail sent to admin").should("exist");
      cy.contains(".w2p_flash", "e-mail sent to submitter").should("exist");
      cy.contains(
        ".w2p_flash",
        "e-mail sent to " + recommender.firstname
      ).should("exist");
    });

    it("Should search for reviewer 1 (co_recommender user)", () => {
      cy.contains(
        ".btn",
        "Choose a reviewer from the PCI Evol Biol DEV database"
      ).click();

      cy.get('#simple-search-input').typeFast(reviewer_1.firstname);
      cy.get('#simple-search-input').type("{enter}");

      cy.contains("a", "Prepare an invitation").should("exist");
    });

    it("Should invite reviewer 1", () => {
      cy.contains("a", "Prepare an invitation").click();

      cy.get("input[type=submit]").click();
    });

    it("=> mail sent to reviewer 1", () => {
      cy.wait(500);
      cy.contains(
        ".w2p_flash",
        "e-mail sent to " + reviewer_1.firstname
      ).should("exist");
    });

    it("Should search for reviewer 2 (developer user)", () => {
      cy.contains(
        ".btn",
        "Choose a reviewer from the PCI Evol Biol DEV database"
      ).click();

      cy.get('#simple-search-input').typeFast(reviewer_2.firstname);
      cy.get('#simple-search-input').type('{enter}');

      cy.contains("a", "Prepare an invitation").should("exist");
    });

    it("Should invite reviewer 2", () => {
      cy.contains("a", "Prepare an invitation").click();

      cy.get("input[type=submit]").click();
    });

    it("=> mail sent to reviewer 2", () => {
      cy.wait(500);
      cy.contains(
        ".w2p_flash",
        "e-mail sent to " + reviewer_2.firstname
      ).should("exist");
    });

    it("Should invite reviewer outside PCI database", () => {
      cy.contains(
        ".btn",
        "Choose a reviewer outside PCI Evol Biol DEV database"
      ).click();

      cy.get("#no_table_reviewer_first_name").typeFast("Titi");
      cy.get("#no_table_reviewer_last_name").typeFast("Toto");
      cy.get("#no_table_reviewer_email").typeFast("ratalatapouet@toto.com");

      cy.get("input[type=submit]").click();
    });

    it("=> mail sent to reviewer outside PCI db", () => {
      cy.wait(500);
      cy.contains(".w2p_flash", "e-mail sent to Titi Toto").should("exist");
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

    it("=> reviewer 1 : article correct status", () => {
      cy.pciCheckArticleStatus(
        currentTest,
        reviewer_1,
        "suggested_reviewer",
        "3-Review invitations sent",
        "HANDLING PROCESS UNDERWAY",
        articleTitle
      );
    });

    it("=> reviewer 2 : article correct status", () => {
      cy.pciCheckArticleStatus(
        currentTest,
        reviewer_2,
        "suggested_reviewer",
        "3-Review invitations sent",
        "HANDLING PROCESS UNDERWAY",
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
      cy.contains(
        ".w2p_flash",
        "e-mail sent to " + reviewer_1.firstname
      ).should("exist");
    });

    it("Should write and submit review", () => {
      cy.contains("a", "Write, edit or upload your review").should("exist");
      cy.contains("a", "Write, edit or upload your review").click();

      cy.fixture("fake_datas").then((datas) => {
        // cy.get("#t_reviews_review").typeFast("Review 1 " + datas.long_text);
        cy.get("#t_reviews_review_ifr").typeTinymce(
          "Review 1 " + datas.long_html_text
        );
      });

      cy.get('input[name="terminate"]').click();
      cy.get('#confirm-dialog').click();

    });

    it("=> mail sent to recommender and current reviewer", () => {
      cy.wait(500);
      cy.contains(
        ".w2p_flash",
        "e-mail sent to " + recommender.firstname
      ).should("exist");
      cy.contains(
        ".w2p_flash",
        "e-mail sent to " + reviewer_1.firstname
      ).should("exist");
    });

    it("Should have 'Request(s) to handle a preprint' enhanced menu", () => {
      cy.contains(".dropdown-toggle", "For contributors").click();
      cy.contains("a", "Your reviews").click();

      cy.get(".cyp-review-state").first().should("contain", "COMPLETED");

      cy.contains("a", "View / Edit").first().click();

      cy.contains("a", "Write, edit or upload your review").should("not.exist");
    });
  });

  //######################################################################################################################################
  describe("Reviewer 2 : Accept and submit review", () => {
    before(() => {
      // log as normal_user

      cy.pciLogin(reviewer_2);
    });

    it("Should have 'Request(s) to handle a preprint' enhanced menu", () => {
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
      cy.contains(
        ".w2p_flash",
        "e-mail sent to " + reviewer_2.firstname
      ).should("exist");
    });

    it("Should write and submit review", () => {
      cy.contains("a", "Write, edit or upload your review").should("exist");
      cy.contains("a", "Write, edit or upload your review").click();

      cy.fixture("fake_datas").then((datas) => {
        // cy.get("#t_reviews_review").typeFast("Review 2 " + datas.long_text);
        cy.get("#t_reviews_review_ifr").typeTinymce(
          "Review 2 " + datas.long_html_text
        );
      });

      cy.get('input[name="terminate"]').click();
      cy.get('#confirm-dialog').click();
    });

    it("=> mail sent to recommender and current reviewer", () => {
      cy.wait(500);
      cy.contains(
        ".w2p_flash",
        "e-mail sent to " + recommender.firstname
      ).should("exist");
      cy.contains(
        ".w2p_flash",
        "e-mail sent to " + reviewer_2.firstname
      ).should("exist");
    });

    it("Should have 'Request(s) to handle a preprint' enhanced menu", () => {
      cy.contains(".dropdown-toggle", "For contributors").click();
      cy.contains("a", "Your reviews").click();

      cy.get(".cyp-review-state").first().should("contain", "COMPLETED");

      cy.contains("a", "View / Edit").first().click();

      cy.contains("a", "Write, edit or upload your review").should("not.exist");
    });
  });

  //######################################################################################################################################
  describe("4 - Reviews submitted => check status : HANDLING PROCESS UNDERWAY", () => {
    it("=> submitter : article correct status", () => {
      cy.pciCheckArticleStatus(
        currentTest,
        submitter,
        "submitter",
        "4-Reviews submitted",
        "HANDLING PROCESS UNDERWAY",
        articleTitle
      );
    });

    it("=> manager : article correct status", () => {
      cy.pciCheckArticleStatus(
        currentTest,
        manager,
        "manager",
        "4-Reviews submitted",
        "HANDLING PROCESS UNDERWAY",
        articleTitle
      );
    });

    it("=> recommender : article correct status", () => {
      cy.pciCheckArticleStatus(
        currentTest,
        recommender,
        "recommender",
        "4-Reviews submitted",
        "HANDLING PROCESS UNDERWAY",
        articleTitle
      );
    });

    it("=> reviewer 1 : article correct status", () => {
      cy.pciCheckArticleStatus(
        currentTest,
        reviewer_1,
        "reviewer",
        "4-Reviews submitted",
        "HANDLING PROCESS UNDERWAY",
        articleTitle
      );
    });

    it("=> reviewer 2 : article correct status", () => {
      cy.pciCheckArticleStatus(
        currentTest,
        reviewer_2,
        "reviewer",
        "4-Reviews submitted",
        "HANDLING PROCESS UNDERWAY",
        articleTitle
      );
    });
  });

  //######################################################################################################################################
  describe("Recommender : Write recommendation decision 'Validation'", () => {
    before(() => {
      // log as normal_user

      cy.pciLogin(recommender);
    });

    it("Should have 'Preprint(s) you are handling' enhanced menu", () => {
      cy.contains(".pci-enhancedMenuItem", "For recommenders").should("exist");
      cy.contains(".dropdown-toggle", "For recommenders").click();

      cy.contains(
        ".pci-enhancedMenuItem",
        "Preprint(s) you are handling"
      ).should("exist");
      cy.contains("a", "Preprint(s) you are handling").click();
    });

    it("Should show article in 'Preprint(s) you are handling' page", () => {
      cy.contains("tr", articleTitle).should("exist");

      // cy.get(".pci-status")
      //   .first()
      //   .should("contain", "HANDLING PROCESS UNDERWAY");
    });

    it("Should write recommendation decision", () => {
      cy.contains("a", "View / Edit").first().click();

      cy.contains("a", "Write or edit your decision / recommendation").click();

      cy.get("#opinion_recommend").click();

      cy.fixture("fake_datas").then((datas) => {
        cy.get("#t_recommendations_recommendation_title").typeFast(
          recommTitle + " " + datas.small_text
        );

        // cy.get("#t_recommendations_recommendation_comments").typeFast(
        //   "Recomm " + datas.long_text
        // );
        cy.get("#t_recommendations_recommendation_comments_ifr").typeTinymce(
          "Recomm " + datas.long_html_text
        );
      });

      cy.get('input[name="terminate"]').click();
    });

    it("=> mail sent to manager and recommender", () => {
      cy.wait(500);
      cy.contains(".w2p_flash", "Recommendation saved and completed");
      cy.contains(".w2p_flash", "e-mail sent to manager").should("exist");
      cy.contains(
        ".w2p_flash",
        "e-mail sent to " + recommender.firstname
      ).should("exist");
    });

    it("Should show article under status 'RECOMMENDATION PENDING VALIDATION'", () => {
      cy.contains("tr", articleTitle).should("exist");

      // cy.get(".pci-status")
      //   .first()
      //   .should("contain", "RECOMMENDATION PENDING VALIDATION");
    });
  });

  //######################################################################################################################################
  describe("5 - Recommendation sent => Verify article status : RECOMMENDATION PENDING VALIDATION", () => {
    it("=> submitter : article correct status", () => {
      cy.pciCheckArticleStatus(
        currentTest,
        submitter,
        "submitter",
        "5-Recommendation sent",
        "HANDLING PROCESS UNDERWAY",
        articleTitle
      );
    });

    it("=> manager : article correct status", () => {
      cy.pciCheckArticleStatus(
        currentTest,
        manager,
        "manager",
        "5-Recommendation sent",
        "RECOMMENDATION PENDING VALIDATION",
        articleTitle
      );
    });

    it("=> recommender : article correct status", () => {
      cy.pciCheckArticleStatus(
        currentTest,
        recommender,
        "recommender",
        "5-Recommendation sent",
        "RECOMMENDATION PENDING VALIDATION",
        articleTitle
      );
    });

    it("=> reviewer 1 : article correct status", () => {
      cy.pciCheckArticleStatus(
        currentTest,
        reviewer_1,
        "reviewer",
        "5-Recommendation sent",
        "HANDLING PROCESS UNDERWAY",
        articleTitle
      );
    });

    it("=> reviewer 2 : article correct status", () => {
      cy.pciCheckArticleStatus(
        currentTest,
        reviewer_2,
        "reviewer",
        "5-Recommendation sent",
        "HANDLING PROCESS UNDERWAY",
        articleTitle
      );
    });
  });

  //##################################################################################################################################
  describe(" Manager : Validate recommendation", () => {
    before(() => {
      // log as manager

      cy.pciLogin(manager);
    });

    it("Should have 'Pending validation(s)' enhanced menu", () => {
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
        .should("contain", "RECOMMENDATION PENDING VALIDATION");
    });

    it("Should validate the recommendation", () => {
      cy.contains("a", "View / Edit").first().click();

      cy.contains("a", "Validate this recommendation").should("exist");
      cy.contains("a", "Validate this recommendation").click();
    });

    it("=> mail sent to all involved", () => {
      cy.wait(500);
      cy.contains(
        ".w2p_flash",
        "e-mail sent to admin " + admin.mail
      ).should("exist");
      cy.contains(
        ".w2p_flash",
        "e-mail sent to " + recommender.firstname
      ).should("exist");
      cy.contains(
        ".w2p_flash",
        "e-mail sent to " + reviewer_1.firstname
      ).should("exist");
      cy.contains(
        ".w2p_flash",
        "e-mail sent to " + reviewer_2.firstname
      ).should("exist");
      cy.contains(
        ".w2p_flash",
        "e-mail sent to submitter " + submitter.firstname
      ).should("exist");
    });
  });

  //##################################################################################################################################
  describe("6 - RECOMMENDED => check status : RECOMMENDED", () => {
    it("=> submitter : article correct status", () => {
      cy.pciCheckArticleStatus(
        currentTest,
        submitter,
        "submitter",
        "6-RECOMMENDED",
        "RECOMMENDED",
        articleTitle
      );
    });

    it("=> manager : article correct status", () => {
      cy.pciCheckArticleStatus(
        currentTest,
        manager,
        "manager",
        "6-RECOMMENDED",
        "RECOMMENDED",
        articleTitle
      );
    });

    it("=> recommender : article correct status", () => {
      cy.pciCheckArticleStatus(
        currentTest,
        recommender,
        "recommender",
        "6-RECOMMENDED",
        "RECOMMENDED",
        articleTitle
      );
    });

    it("=> reviewer 1 : article correct status", () => {
      cy.pciCheckArticleStatus(
        currentTest,
        reviewer_1,
        "reviewer",
        "6-RECOMMENDED",
        "RECOMMENDED",
        articleTitle
      );
    });

    it("=> reviewer 2 : article correct status", () => {
      cy.pciCheckArticleStatus(
        currentTest,
        reviewer_2,
        "reviewer",
        "6-RECOMMENDED",
        "RECOMMENDED",
        articleTitle
      );
    });
  });

  if (!Cypress.env("keepArticle")) {
    //##################################################################################################################################
    describe("Manager : Delete preprint", () => {
      it("Should delete article", () => {
        cy.pciDeleteWithTestLastArticle(articleTitle);
      });
    });

    //##################################################################################################################################
    describe("DELETED => check article not exist", () => {
      it("=> submitter : article not exist", () => {
        cy.pciCheckArticleStatus(
          currentTest,
          submitter,
          "submitter",
          "",
          "not.exist",
          articleTitle
        );
      });

      it("=> recommender : article not exist", () => {
        cy.pciCheckArticleStatus(
          currentTest,
          recommender,
          "recommender",
          "",
          "not.exist",
          articleTitle
        );
      });

      it("=> manager : article not exist", () => {
        cy.pciCheckArticleStatus(
          currentTest,
          manager,
          "manager",
          "",
          "not.exist",
          articleTitle
        );
      });

      it("=> reviewer 1 : article not exist", () => {
        cy.pciCheckArticleStatus(
          currentTest,
          reviewer_1,
          "reviewer",
          "",
          "not.exist",
          articleTitle
        );
      });

      it("=> reviewer 2 : article not exist", () => {
        cy.pciCheckArticleStatus(
          currentTest,
          reviewer_2,
          "reviewer",
          "",
          "not.exist",
          articleTitle
        );
      });
    });
  }
});
