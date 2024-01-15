from conftest import config
from conftest import visit, select, lookup
import requests

base_url = config.base_url


def test_about_version():
    visit(base_url + "/about/version")
    select("#main-content").contains("HEAD -> ")

def test_about_click():
    visit(base_url)
    lookup(".dropdown-toggle", "About").click()

def test_advertize_coar_inbox():
    resp = requests.head(base_url)
    inbox = resp.links['http://www.w3.org/ns/ldp#inbox']['url']
    assert "coar_notify/inbox" in inbox
