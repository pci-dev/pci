from conftest import config
from conftest import visit, select, lookup

base_url = config.base_url


def test_about_version():
    visit(base_url + "/about/version")
    select("#main-content").contains("HEAD -> ")

def test_about_click():
    visit(base_url)
    lookup(".dropdown-toggle", "About").click()
