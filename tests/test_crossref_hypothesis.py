from conftest import config, test
from conftest import login, logout
from conftest import visit, select

base_url = config.base_url


@test
class Login:

    def login_as_admin(_):
        login(config.users.admin)


@test
class Crossref_basic:

    def crossref_post_form_access(_):
        visit(base_url + "/crossref/post_form?article_id=1")

    def crossref_post_form_no_article_specified(_):
        visit(base_url + "/crossref/post_form")
        select("#main-content div pre").contains("article_id: no such parameter")

    def crossref_post_form_no_such_article(_):
        visit(base_url + "/crossref/post_form?article_id=1000")
        select("#main-content div pre").contains("article: no such article")


@test
class Hypothesis_basic:

    def hypothesis_post_form_access(_):
        visit(base_url + "/hypothesis/post_form?article_id=1")


@test
class Logout:

    def logout(_):
        logout(config.users.admin)
