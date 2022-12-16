from selenium.webdriver.common.by import By
from selenium import webdriver
from argparse import Namespace
from os import getenv

def get_driver():
    options = webdriver.chrome.options.Options()
    options.headless = not getenv("SHOW")
    options.add_argument("--window-size=1920x1080")
    return webdriver.Chrome(options=options)

def get_config():
    base_url = "http://localhost:8000/pci"
    users = [ "user", "reviewer", "recommender", "manager", "admin", "test" ]
    return Namespace(
            base_url = base_url,
            users = users_dict(users),
    )

def users_dict(users):
    return Namespace(**{
        user: Namespace(
                name=user,
                email=user+"@pci.org",
                password="pci")
        for user in users
    })


driver = get_driver()
config = get_config()


# Test class decorator

from types import FunctionType

def test(c):
    for fun in c.__dict__.values():
        if type(fun) == FunctionType:
            fun.__test__ = True
    c.__test__ = True
    return c
test.__test__ = False


# Selenium extensions

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement
from time import sleep

def wait_clickable(self):
    WebDriverWait(driver, timeout=5).until(EC.element_to_be_clickable(self))
    sleep(.1)
    return self

def element_contains(self, text):
    assert(text in self.text)

def element_select(self, css, text="", contains=""):
    return select(css, text=text, contains=contains, _=self)

from contextlib import contextmanager

@contextmanager
def element_frame(self):
    driver.switch_to.frame(self)
    yield self
    driver.switch_to.default_content()


WebElement.wait_clickable = wait_clickable
WebElement.contains = element_contains
WebElement.select = element_select
WebElement.frame = element_frame


# HELPERS

def visit(url):
    return driver.get(url)

def select(css, text="", contains="", _=driver):
    if text or contains:
        return lookup(css, text, contains, _=_)
    sel = _.find_elements(By.CSS_SELECTOR, css)
    return sel if len(sel) > 1 else sel[0]

def lookup(css, text="", contains="", _=driver):
    for e in _.find_elements(By.CSS_SELECTOR, css):
        print(f"e.text='{e.text}'")
        if text and (text == e.text):
            print(f"text={text}")
            return e
        if contains and (contains in e.text):
            print(f"contains={contains}")
            return e
    raise KeyError("no such element: " + text)

def login(user):
    visit(config.base_url)
    select(".dropdown-toggle", "Log in").click()
    select(".dropdown-menu li", "Log in").click()
    select("#auth_user_email").send_keys(user.email)
    select("#auth_user_password").send_keys(user.password)
    select("input.btn").click()
    select(".w2p_flash.alert", "Logged in").wait_clickable().click()

def logout(user):
    select(".dropdown-toggle", user.name).click()
    select(".dropdown-menu li", "Log out").click()
    select(".w2p_flash.alert", "Logged out").wait_clickable().click()

from configparser import ConfigParser

def is_rr():
    config = ConfigParser()
    config.read("../private/appconfig.ini")
    return config["config"].getboolean("registered_reports")

def config_set_scheduled_track(value=getenv("RR_SCHEDULED_TRACK")):
    if config.is_rr:
        config.is_rr = Namespace(scheduled_track=value)

config.is_rr = is_rr()
config_set_scheduled_track()



import sys

modules = []
before = []

def begin_import():
    global before
    before = sys.modules.copy()

def end_import():
    global modules
    after = sys.modules
    modules += [m for m in after if not m in before]

def pytest_collection_modifyitems(items):
    _items = []
    for module in modules:
        _items += [ it for it in items if it.function.__module__ == module ]
    _items += [ it for it in items if it not in _items ]
    items[:] = _items


import pytest
@pytest.fixture(scope="class")
def store():
    class _: pass
    return _
