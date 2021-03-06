from conftest import config, select
from conftest import login, logout

user = config.users.test


def test_login():
    login(user)

def test_after_login():
    select(".dropdown-toggle", user.name).click()
    select("ul.dropdown-menu li", "Public page")

def test_logout():
    logout(user)

import pytest
@pytest.mark.parametrize("user", config.users.__dict__.values())
def test_users(user):
    login(user)
    logout(user)
