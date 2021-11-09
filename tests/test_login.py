from conftest import config, select
from conftest import login

user = config.users.test


def test_login():
    login(user)

def test_after_login():
    select(".dropdown-toggle", user.name).click()
    select("ul.dropdown-menu li", "Public page")
