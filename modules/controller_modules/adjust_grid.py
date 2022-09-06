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

remove_options = ['auth_user.registration_key',# 'auth_user.website',
                  'auth_user.alerts', 'auth_user.last_alert', 'auth_user.registration_datetime',
                  'auth_user.ethical_code_approved']
remove_regulators = ['=', '<=', '!=', '<', '>', '>=', 'starts with', 'in', 'not in']
hijacks_all_field = {'users': 'w2p_field_auth_user-id', 'templates': 'w2p_field_mail_templates-lang',
                     'reviewers': 'w2p_field_qy_reviewers-id', 'recommenders': 'w2p_field_qy_recomm-id'}
hijacks_thematics_field = {'users': 'w2p_field_auth_user-website', 'reviewers': 'w2p_field_qy_reviewers-roles',
                           'recommenders': 'w2p_field_qy_recomm-laboratory'}
hijack_values = ['auth_user.id', 'mail_templates.lang', 'qy_reviewers.id', 'qy_recomm.id']


def adjust_grid_basic(grid, search_name, thematics = []):
    '''
    function that adjusts the grid after its generation
    '''
    # gather elements
    web2py_grid = grid.elements('div.web2py_grid')[0]

    panel = grid.elements('div#w2p_query_panel')[0]
    btns = grid.elements('input.btn-default')
    select_panel = grid.elements('select#w2p_query_fields')[0]
    regulator_panels = grid.elements('select.form-control')
    search_field = grid.elements('.web2py_console form')[0]

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
        panel_search_field2 = grid.elements('div#w2p_field_auth_user-website')[0]
        select_panel_id = grid.elements('#w2p_field_auth_user-id select.form-control')[0]
        select_panel_id2 = grid.elements('#w2p_field_auth_user-website select.form-control')[0]
        # restyle the add button
        add_btn = grid.elements('div.web2py_console a.btn-secondary')[0]
        add_btn.__getattribute__('attributes').update({'_style':'margin-bottom:4rem'})
    elif search_name == 'reviewers':
        panel_search_field = grid.elements('div#w2p_field_qy_reviewers-id')[0]
        panel_search_field.__getattribute__('attributes').update({'_style':'display:flex'})
        panel_search_field2 = grid.elements('div#w2p_field_qy_reviewers-roles')[0]
        select_panel_id = grid.elements('#w2p_field_qy_reviewers-id select.form-control')[0]
        select_panel_id2 = grid.elements('#w2p_field_qy_reviewers-roles select.form-control')[0]
    elif search_name == 'recommenders':
        panel_search_field = grid.elements('div#w2p_field_qy_recomm-id')[0]
        panel_search_field.__getattribute__('attributes').update({'_style':'display:flex'})
        panel_search_field2 = grid.elements('div#w2p_field_qy_recomm-laboratory')[0]
        select_panel_id = grid.elements('#w2p_field_qy_recomm-id select.form-control')[0]
        select_panel_id2 = grid.elements('#w2p_field_qy_recomm-laboratory select.form-control')[0]


    # restyle Add, And, Or, Close buttons
    for btn in btns:
        if btn.__getattribute__('attributes')['_value'] == 'New Search':
            #btn.__getattribute__('attributes').update({'_value':'ADD'})
            btn.__getattribute__('attributes').update({'_class':'btn btn-default add-btn'})
        elif btn.__getattribute__('attributes')['_value'] == '+ And':
            btn.__getattribute__('attributes').update({'_style':'display:none'})
            btn.__getattribute__('attributes').update({'_class':'btn btn-default and-btn'})
        elif btn.__getattribute__('attributes')['_value'] == '+ Or':
            btn.__getattribute__('attributes').update({'_style':'display:none'})
            btn.__getattribute__('attributes').update({'_class':'btn btn-default or-btn'})
        elif btn.__getattribute__('attributes')['_value'] == 'Close':
            btn.__getattribute__('attributes').update({'_style':'display:none'})
    
    # initially, the ADD buttons are now green SEARCH buttons
    add_btns = grid.elements('div#w2p_query_panel input.add-btn')
    for ab in add_btns:
        ab.__getattribute__('attributes').update({'_value':'SEARCH'})
        ab.__getattribute__('attributes').update({'_style':'background-color:#93c54b'})
        ab.__getattribute__('attributes').update({'_onclick':'new_search(this)'})

    # initially, the large search field is hidden
    search_field.__getattribute__('attributes').update({'_style': 'display:none'})

    # hi-jack unused ID field and re-create it to an "All Fields" search
    hijack_field = hijacks_all_field[search_name]
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
            input.__getattribute__('attributes').update({'_onclick': 'add_all(this, "new", "' + search_name + '")'})
            input.__getattribute__('attributes').update({'_value': 'SEARCH'})
            input.__getattribute__('attributes').update({'_style': 'background-color:#93c54b'})
        if 'and-btn' in input.__getattribute__('attributes')['_class']:
            input.__getattribute__('attributes').update({'_onclick': 'add_all(this, "and", "' + search_name + '")'})
        if 'or-btn' in input.__getattribute__('attributes')['_class']:
            input.__getattribute__('attributes').update({'_onclick': 'add_all(this, "or", "' + search_name + '")'})
        if 'not-btn' in input.__getattribute__('attributes')['_class']:
            input.__getattribute__('attributes').update({'_onclick': 'add_all(this, "not", "' + search_name + '")'})

    panel_search_field.__getattribute__('attributes').update({'_id': 'w2p_field_all'})

    if thematics:
        # hi-jack unused field and re-create it to an "Thematics" search
        try:
            hijack_field2 = hijacks_thematics_field[search_name]
            regulator_panel_id2 = grid.elements('div#%s .form-control'%hijack_field2)
            options2 = regulator_panel_id2[0].elements('option')
            for i,option in enumerate(options2):
                if i >= len(thematics):
                    option.__getattribute__('attributes').update({'_class': 'remove'}) # assign class to allow selection
                    select_panel_id2.elements('option.remove', replace='') # then select and remove
                else:
                    option.__getattribute__('attributes').update({'_class': 'hijack'}) # assign class to allow selection
                    select_panel_id2.elements('option.hijack', replace=OPTION(thematics[i], _class=thematics[i])) # then select and replace
                    option.__getattribute__('attributes').update({'_style':'display:none'})
            
            input_fields_id = regulator_panel_id2[0].siblings()
            for input in input_fields_id:
                if 'form-control' in input.__getattribute__('attributes')['_class']:
                    input.__getattribute__('attributes').update({'_id': 'w2p_value_thematics'})
                    input.__getattribute__('attributes').update({'_class': 'thematics form-control'})
                    input.__getattribute__('attributes').update({'_disabled':'disabled'})
                if 'add-btn' in input.__getattribute__('attributes')['_class']:
                    input.__getattribute__('attributes').update({'_onclick': 'add_thematics("' + search_name + '", "new")'})
                if 'and-btn' in input.__getattribute__('attributes')['_class']:
                    input.__getattribute__('attributes').update({'_onclick': 'add_thematics("' + search_name + '", "and")'})
                if 'or-btn' in input.__getattribute__('attributes')['_class']:
                    input.__getattribute__('attributes').update({'_onclick': 'add_thematics("' + search_name + '", "or")'})
                if 'not-btn' in input.__getattribute__('attributes')['_class']:
                    input.__getattribute__('attributes').update({'_onclick': 'add_thematics("' + search_name + '", "not", true)'})

            panel_search_field2.__getattribute__('attributes').update({'_id': 'w2p_field_thematics'})
        except:
            print('Thematic Field Creation Failed')

    # remove options, regulators, and other elements that are not required
    for option in select_panel:
        if option.__getattribute__('attributes')['_value'] in hijack_values:
            option.__getattribute__('attributes').update({'_class':'selector'})
            grid.elements('div#w2p_field_all')[0].__getattribute__('attributes').update({'_style':'display:flex'})
        elif option.__getattribute__('attributes')['_value'] == 'auth_user.website':
            option.__getattribute__('attributes').update({'_class':'selector'})
            select_panel.elements('option.selector', replace=OPTION('Thematic Fields', _value="thematics", _class="thematics"))
            new_thematics_field = select_panel.elements('option.thematics')
            select_panel.elements('option.thematics', replace=None)
            grid.elements('select#w2p_query_fields')[0].insert(1,new_thematics_field[0]) # set Thematic fields to 2nd position
        elif option.__getattribute__('attributes')['_value'] == 'qy_reviewers.roles':
            option.__getattribute__('attributes').update({'_class':'selector'})
            select_panel.elements('option.selector', replace=OPTION('Thematic Fields', _value="thematics", _class="thematics"))
            new_thematics_field = select_panel.elements('option.thematics')
            select_panel.elements('option.thematics', replace=None)
            grid.elements('select#w2p_query_fields')[0].insert(1,new_thematics_field[0]) # set Thematic fields to 2nd position            
        # remove the fields that are not required
        elif option.__getattribute__('attributes')['_value'] in remove_options:
            option.__getattribute__('attributes').update({'_style':'display:none'})
            grid.elements('div#w2p_field_' + option.__getattribute__('attributes')['_value'].replace('.', '-'), replace=None)
    
    # set "All Fields" as primary choice
    for option in select_panel:
        if option.__getattribute__('attributes')['_value'].endswith('.any'):
            option.__getattribute__('attributes').update({'_selected':'selected'})

    for selector in regulator_panels:
        options = selector.elements('option')
        for option in options:
            if option.__getattribute__('attributes')['_value'] == 'contains':
                option.__getattribute__('attributes').update({'_selected':'selected'})
                #selector.__getattribute__('attributes').update({'_disabled':'disabled'}) 
            elif option.__getattribute__('attributes')['_value'] == '!=':
                option.__getattribute__('attributes').update({'_class': 'not_contains'})
                selector.elements('option.not_contains', replace=OPTION('not contains', _class="not_contains"))                
            elif option.__getattribute__('attributes')['_value'] in remove_regulators:
                option.__getattribute__('attributes').update({'_style':'display:none'})
        #selector.__getattribute__('attributes').update({'_style':'display:none'})

    grid.elements('div#w2p_query_panel', replace=None)
    grid.elements('div.web2py_breadcrumbs', replace=None)
    grid.elements('div.web2py_console a.btn-secondary', replace=None)

    # add elements at different positions
    grid.elements('div.web2py_console ')[0].insert(0, panel)
    if search_name == 'users':
        web2py_grid.insert(0, add_btn)

    return grid

