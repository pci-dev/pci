describe("Check version page", () => {

  describe("Version info without login", () => {
    let site_url;

    before(() => {
      cy.fixture("config").then((config) => {
	      site_url = config.site_url;
      });
    });

    it("Should show version", () => {
      cy.visit(site_url + "about/version");
      cy.contains(/^[a-f0-9]+ .*/).should("exist");
    });
  });

});
