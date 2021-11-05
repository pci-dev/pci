from conftest import config
from conftest import visit, select, lookup

base_url = config.base_url


def login(user_name):
    user = config.users[user_name]
    select(".btn", "LOG IN").click()
    select("#auth_user_email").send_keys(user.email)
    select("#auth_user_password").send_keys(user.password)
    select("input.btn").click()
    select(".w2p_flash.alert", "Logged in")


def test_login():
    visit(base_url)
    user = "test"
    login(user)

def test_after_login():
    visit(base_url)
    user = "test"
    select(".dropdown-toggle", user).click()
    select("ul.dropdown-menu li", "Public page")
