# -*- coding: utf-8 -*-
import re
import copy
import random
import os
import tempfile
import shutil
import datetime

from gluon.contrib.markdown import WIKI

from app_modules.helper import *

from controller_modules import admin_module
from controller_modules import adjust_grid
from app_modules import common_small_html
from app_modules import common_tools
from app_modules import emailing_tools

from app_components import app_forms

from gluon.contrib.markmin.markmin2latex import render, latex_escape

from gluon.contrib.appconfig import AppConfig

remove_options = ['auth_user.registration_key', 'auth_user.website',
                    'auth_user.alerts', 'auth_user.last_alert', 'auth_user.registration_datetime',
                    'auth_user.ethical_code_approved']
remove_regulators = ['=', '<=', '!=', '<', '>', '>=', 'starts with', 'in', 'not in']
hijacks = {'users': 'w2p_field_auth_user-id', 'templates': 'w2p_field_mail_templates-lang', 'reviewers': 'w2p_field_qy_reviewers-id'}
hijack_values = ['auth_user.id', 'mail_templates.lang', 'qy_reviewers.id']

def adjust_grid_basic(grid, search_name):
    '''
    function that adjusts the grid after its generation
    '''
    # gather elements
    panel = grid.elements('div#w2p_query_panel')[0]
    btns = grid.elements('input.btn-default')
    select_panel = grid.elements('select#w2p_query_fields')[0]
    regulator_panels = grid.elements('select.form-control')

    # individual changes
    panel.__getattribute__('attributes').update({'_style':'display:flex'})
    if search_name == 'templates':
        hashtag_regulator = grid.elements('div#w2p_field_mail_templates-hashtag')[0]
        hashtag_regulator.__getattribute__('attributes').update({'_style':'display:none'})
        panel_search_field = grid.elements('div#w2p_field_mail_templates-lang')[0]
        select_panel_id = grid.elements('#w2p_field_mail_templates-lang select.form-control')[0]
    elif search_name == 'users':
        panel_search_field = grid.elements('div#w2p_field_auth_user-id')[0]
        panel_search_field.__getattribute__('attributes').update({'_style':'display:flex'})
        select_panel_id = grid.elements('#w2p_field_auth_user-id select.form-control')[0]
    elif search_name == 'reviewers':
        panel_search_field = grid.elements('div#w2p_field_qy_reviewers-id')[0]
        panel_search_field_roles = grid.elements('div#w2p_field_qy_reviewers-id')[0]
        panel_search_field_roles.__getattribute__('attributes').update({'_style':'display:flex'})
        select_panel_id = grid.elements('#w2p_field_qy_reviewers-id select.form-control')[0]

    # restyle the add button
    if search_name == 'users':
        add_btn = grid.elements('div.web2py_console a.btn-secondary')[0]
        add_btn.__getattribute__('attributes').update({'_style':'margin-bottom:4rem'})

    # restyle Add, And, Or, Close buttons
    for btn in btns:
        if btn.__getattribute__('attributes')['_value'] == 'New Search':
            btn.__getattribute__('attributes').update({'_value':'ADD'})
            btn.__getattribute__('attributes').update({'_class':'btn btn-default add-btn'})
        elif btn.__getattribute__('attributes')['_value'] == '+ And':
            btn.__getattribute__('attributes').update({'_style':'display:none'})
            btn.__getattribute__('attributes').update({'_class':'btn btn-default and-btn'})
        elif btn.__getattribute__('attributes')['_value'] == '+ Or':
            btn.__getattribute__('attributes').update({'_style':'display:none'})
            btn.__getattribute__('attributes').update({'_class':'btn btn-default or-btn'})
        elif btn.__getattribute__('attributes')['_value'] == 'Close':
            btn.__getattribute__('attributes').update({'_style':'display:none'})

    # hi-jack one unused field and re-create it to an "All Fields" search
    hijack_field = hijacks[search_name]
    regulator_panel_id = grid.elements('div#%s .form-control'%hijack_field)
    options = regulator_panel_id[0].elements('option')
    for option in options:
        if option.__getattribute__('attributes')['_value'] == '=':
            option.__getattribute__('attributes').update({'_class': 'contains'})
            select_panel_id.elements('option.contains', replace=OPTION('contains', _class="contains"))
        option.__getattribute__('attributes').update({'_style':'display:none'})

    input_fields_id = regulator_panel_id[0].siblings()
    for input in input_fields_id:
        if 'form-control' in input.__getattribute__('attributes')['_class']:
            input.__getattribute__('attributes').update({'_id': 'w2p_value_all'})
            input.__getattribute__('attributes').update({'_class': 'all form-control'})
        if 'add-btn' in input.__getattribute__('attributes')['_class']:
            input.__getattribute__('attributes').update({'_onclick': 'add_all(this, "new")'})
        if 'and-btn' in input.__getattribute__('attributes')['_class']:
            input.__getattribute__('attributes').update({'_onclick': 'add_all(this, "AND")'})
        if 'or-btn' in input.__getattribute__('attributes')['_class']:
            input.__getattribute__('attributes').update({'_onclick': 'add_all(this, "OR")'})
        if 'not-btn' in input.__getattribute__('attributes')['_class']:
            input.__getattribute__('attributes').update({'_onclick': 'add_all(this, "NOT")'})

    panel_search_field.__getattribute__('attributes').update({'_id': 'w2p_field_all'})

    # remove options, regulators, and other elements that are not required
    for option in select_panel:
        if option.__getattribute__('attributes')['_value'] in hijack_values:
            option.__getattribute__('attributes').update({'_class':'selector'})
            select_panel.elements('option.selector', replace=OPTION('All fields', _value="all"))
            grid.elements('div#w2p_field_all')[0].__getattribute__('attributes').update({'_style':'display:flex'})
        # remove the fields that are not required
        elif option.__getattribute__('attributes')['_value'] in remove_options:
            option.__getattribute__('attributes').update({'_style':'display:none'})
            grid.elements('div#w2p_field_' + option.__getattribute__('attributes')['_value'].replace('.', '-'), replace=None)
    
    # set "All Fields" as primary choice
    for option in select_panel:
        if option.__getattribute__('attributes')['_value'] == 'all':
            option.__getattribute__('attributes').update({'_selected':'selected'})

    for selector in regulator_panels:
        options = selector.elements('option')
        for option in options:
            if option.__getattribute__('attributes')['_value'] == 'contains':
                option.__getattribute__('attributes').update({'_selected':'selected'})
                selector.__getattribute__('attributes').update({'_disabled':'disabled'}) 
            elif option.__getattribute__('attributes')['_value'] in remove_regulators:
                option.__getattribute__('attributes').update({'_style':'display:none'})

    grid.elements('div#w2p_query_panel', replace=None)
    grid.elements('div.web2py_breadcrumbs', replace=None)
    grid.elements('div.web2py_console a.btn-secondary', replace=None)

    # add elements at different positions
    grid.elements('div.web2py_console ')[0].insert(0, panel)
    if search_name == 'users':
        grid.elements('div.web2py_console ')[0].insert(0, add_btn)

    return grid

