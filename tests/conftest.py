from selenium.webdriver.common.by import By
from selenium import webdriver
from argparse import Namespace
from os import getenv

DEFAULT_TIMEOUT = int(5)
DEFAULT_SLEEP = int(1)

def get_driver():
    options = webdriver.firefox.options.Options()
    options.add_argument("--headless") if not getenv("show") else None
    return webdriver.Firefox(options=options)

def get_config():
    base_url = "http://localhost:8000"
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
users = config.users

driver.set_window_size(1500, 1000)
driver.implicitly_wait(5)


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
    WebDriverWait(driver, timeout=DEFAULT_TIMEOUT).until(EC.element_to_be_clickable(self))
    sleep(DEFAULT_SLEEP)
    return self

def element_contains(self, text):
    assert(text in self.text)

def element_select(self, css, text="", contains=""):
    return select(css, text=text, contains=contains, _=self)

from contextlib import contextmanager

@contextmanager
def element_frame(self):
    driver.switch_to.frame(self)
    self.click()
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
    sel = WebDriverWait(_, timeout=DEFAULT_TIMEOUT).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, css)))
    return sel if len(sel) > 1 else sel[0]

def lookup(css, text="", contains="", _=driver):
    try:
        elements = WebDriverWait(_, timeout=DEFAULT_TIMEOUT).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, css)))
    except:
        elements = []
    for e in elements:
        print(f"e.text='{e.text}'")
        if text and (text == e.text):
            print(f"text={text}")
            return e
        if contains and (contains in e.text):
            print(f"contains={contains}")
            return e
    raise KeyError("no such element: " + text)

def select_notif(text="", contains=""):
    sleep(DEFAULT_SLEEP)
    return select(".w2p_flash", text=text, contains=contains)

select.notif = select_notif


def check_fails(func):
    def fails(*args, **kwargs):
        with pytest.raises(KeyError):
            func(*args, **kwargs)
    return fails

select.fails = check_fails(select)
lookup.fails = check_fails(lookup)

def login(user):
    visit(config.base_url)
    select(".dropdown-toggle", "Log in").click()
    select(".dropdown-menu li", "Log in").click()
    select("#auth_user_email").send_keys(user.email)
    select("#auth_user_password").send_keys(user.password)
    select("input.btn").click()
    select.notif("Logged in").wait_clickable().click()

def logout(user):
    select(".dropdown-toggle", user.name).click()
    select(".dropdown-menu li", "Log out").click()
    select.notif("Logged out").wait_clickable().click()

from configparser import ConfigParser

def get_web2py_config():
    config = ConfigParser()
    config.read("../private/appconfig.ini")
    return config

w2p_config = get_web2py_config()


def config_set_scheduled_track(value=getenv("RR_SCHEDULED_TRACK")):
    if config.is_rr:
        config.is_rr = Namespace(scheduled_track=value)

config.is_rr = w2p_config["config"].getboolean("registered_reports")
config_set_scheduled_track()
config.reco_private = getenv("reco_private")


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
