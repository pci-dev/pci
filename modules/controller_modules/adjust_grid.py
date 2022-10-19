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

remove_options = ['auth_user.registration_key', 'auth_user.alerts', 
                  'auth_user.last_alert', 'auth_user.registration_datetime',
                  'auth_user.ethical_code_approved', 'qy_recomm.id', 'auth_user.id',
                  'mail_templates.lang', 'qy_reviewers.id',
                  'qy_reviewers.thematics', 'qy_recomm.thematics', 't_articles.id',
                  't_articles.upload_timestamp',  't_articles.status',
                  't_articles.last_status_change', 't_status_article.status',
                  't_status_article.color_class', 't_status_article.explaination', 't_status_article.priority_level',
                  't_articles.has_manager_in_authors', 't_articles.picture_rights_ok',
                  't_articles.results_based_on_data', 't_articles.scripts_used_for_result',
                  't_articles.codes_used_in_study', 't_articles.validation_timestamp',
                  't_articles.user_id', 't_articles.request_submission_change', 't_articles.already_published',
                  't_articles.doi_of_published_article', 't_articles.is_searching_reviewers', 't_articles.report_stage',
                  't_articles.art_stage_1_id', 't_articles.record_url_version', 't_articles.sub_thematics',
                  't_articles.record_id_version', 'qy_art.doi', 'qy_art.abstract', 'qy_art.status',
                  'qy_art.last_status_change', 'qy_art.already_published']
remove_regulators = ['=', '<=', '!=', '<', '>', '>=', 'starts with', 'in', 'not in']
hijacks_thematics_field = {'users': 'w2p_field_auth_user-website', 'reviewers': 'w2p_field_qy_reviewers-roles',
                           'recommenders': 'w2p_field_qy_recomm-roles'}
thematics_hijacked_options = ['auth_user.website', 'qy_reviewers.roles', 'qy_recomm.roles']
search_name2field = {'reviewers': 'qy_reviewers', 'users': 'auth_user',
                     'recommenders': 'qy_recomm', 'articles': 't_articles', 'articles_temp': 'qy_art',
                     'articles2': 't_status_article'}


def adjust_grid_basic(grid, search_name, thematics = []):
    '''
    function that adjusts the grid after its generation
    '''
    # gather elements
    web2py_grid = grid.element('div.web2py_grid')
    panel = grid.element('div#w2p_query_panel')
    btns = grid.elements('input.btn-default')
    select_panel = grid.element('select#w2p_query_fields')
    regulator_panels = grid.elements('select.form-control')
    search_field = grid.element('.web2py_console form')
    search_field = grid.element('.web2py_console form')
    panel_query_rows = grid.elements('div#w2p_query_panel div')
    input_buttons = grid.elements('form input.btn')

    # individual changes
    panel.__getattribute__('attributes').update({'_style':'display:flex'})
    if search_name == 'templates':
        panel_search_field = grid.element('div#w2p_field_mail_templates-lang')
    elif search_name == 'users':
        panel_search_field = grid.element('div#w2p_field_auth_user-id')
        panel_search_field.__getattribute__('attributes').update({'_style':'display:flex'})
        panel_search_field2 = grid.element('div#w2p_field_auth_user-website')
        select_panel_id2 = grid.element('#w2p_field_auth_user-website select.form-control')
        # restyle the add button
        add_btn = grid.element('div.web2py_console a.btn-secondary')
        add_btn.__getattribute__('attributes').update({'_style':'margin-bottom:4rem'})
    elif search_name == 'reviewers':
        panel_search_field = grid.element('div#w2p_field_qy_reviewers-id')
        panel_search_field.__getattribute__('attributes').update({'_style':'display:flex'})
        panel_search_field2 = grid.element('div#w2p_field_qy_reviewers-roles')
        select_panel_id2 = grid.element('#w2p_field_qy_reviewers-roles select.form-control')
    elif search_name == 'recommenders':
        panel_search_field = grid.element('div#w2p_field_qy_recomm-id')
        panel_search_field.__getattribute__('attributes').update({'_style':'display:flex'})
        panel_search_field2 = grid.element('div#w2p_field_qy_recomm-roles')
        select_panel_id2 = grid.element('#w2p_field_qy_recomm-roles select.form-control')
    elif search_name == 'articles':
        panel_search_field = grid.element('div#w2p_field_t_articles-id')
        panel_search_field.__getattribute__('attributes').update({'_style':'display:flex'})
    elif search_name == 'articles_temp':
        panel_search_field = grid.element('div#w2p_field_qy_art-id')
        panel_search_field.__getattribute__('attributes').update({'_style':'display:flex'})
    elif search_name == 'articles2':
        panel_search_field = grid.element('div#w2p_field_t_status_article-id')
        panel_search_field.__getattribute__('attributes').update({'_style':'display:flex'})

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

    if thematics:
        # hi-jack unused field and re-create it to an "Thematics" search
        try:
            hijack_field2 = hijacks_thematics_field[search_name]
            regulator_panel_id2 = grid.element('div#%s .form-control'%hijack_field2)
            options2 = regulator_panel_id2.elements('option')
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
                    input.__getattribute__('attributes').update({'_onclick': 'add_thematics("' + search_name2field[search_name] + '", "new")'})
                if 'and-btn' in input.__getattribute__('attributes')['_class']:
                    input.__getattribute__('attributes').update({'_onclick': 'add_thematics("' + search_name2field[search_name] + '", "and")'})
                if 'or-btn' in input.__getattribute__('attributes')['_class']:
                    input.__getattribute__('attributes').update({'_onclick': 'add_thematics("' + search_name2field[search_name] + '", "or")'})
                if 'not-btn' in input.__getattribute__('attributes')['_class']:
                    input.__getattribute__('attributes').update({'_onclick': 'add_thematics("' + search_name2field[search_name] + '", "not", true)'})

            panel_search_field2.__getattribute__('attributes').update({'_id': 'w2p_field_thematics'})
        except:
            print('Thematic Field Creation Failed')

    # remove options, regulators, and other elements that are not required
    for option in select_panel:
        if option.__getattribute__('attributes')['_value'].endswith('any'):
            option.__getattribute__('attributes').update({'_class':'selector'})
            grid.element('div#w2p_field_' + search_name2field[search_name] + '-any').__getattribute__('attributes').update({'_style':'display:flex'})
        # setup Thematic Fields custom control
        if option.__getattribute__('attributes')['_value'] in thematics_hijacked_options:
            option.__getattribute__('attributes').update({'_class':'selector'})
            select_panel.elements('option.selector', replace=OPTION('Thematic Fields', _value="thematics", _class="thematics"))
            new_thematics_field = select_panel.elements('option.thematics')
            select_panel.elements('option.thematics', replace=None)
            grid.element('select#w2p_query_fields').insert(1,new_thematics_field[0]) # set Thematic fields to 2nd position
        # remove the fields that are not required
        elif option.__getattribute__('attributes')['_value'] in remove_options:
            option.__getattribute__('attributes').update({'_style':'display:none'})
            grid.elements('div#w2p_field_' + option.__getattribute__('attributes')['_value'].replace('.', '-'), replace=None)

    # set "All Fields" as primary choice
    for option in select_panel:
        if option.__getattribute__('attributes')['_value'].endswith('.any'):
            option.__getattribute__('attributes').update({'_selected':'selected'})

    # in list_users(), where we have no "All fields", set "First name" as primary choice.
    # similarly, in mail_templates we set "Hashtag" as primary choice.
    if search_name == 'users':
        for option in select_panel:
            if option.__getattribute__('attributes')['_value'].endswith('.first_name'):
                option.__getattribute__('attributes').update({'_selected':'selected'})
                first_name_input_field = grid.element('div#w2p_field_auth_user-first_name')
                first_name_input_field.__getattribute__('attributes').update({'_style':'display:flex'})
    elif search_name == 'templates':
        for option in select_panel:
            if option.__getattribute__('attributes')['_value'].endswith('.hashtag'):
                option.__getattribute__('attributes').update({'_selected':'selected'})
                hashtag_input_field = grid.element('div#w2p_field_mail_templates-hashtag')
                hashtag_input_field.__getattribute__('attributes').update({'_style':'display:flex'})
    elif search_name == 'articles':
        for option in select_panel:
            if option.__getattribute__('attributes')['_value'].endswith('.title'):
                option.__getattribute__('attributes').update({'_selected':'selected'})
                title_input_field = grid.element('div#w2p_field_t_articles-title')
                title_input_field.__getattribute__('attributes').update({'_style':'display:flex'}) 
    elif search_name == 'articles_temp':
        for option in select_panel:
            if option.__getattribute__('attributes')['_value'].endswith('.title'):
                option.__getattribute__('attributes').update({'_selected':'selected'})
                title_input_field = grid.element('div#w2p_field_qy_art-title')
                title_input_field.__getattribute__('attributes').update({'_style':'display:flex'})
    elif search_name == 'articles2':
        for option in select_panel:
            if option.__getattribute__('attributes')['_value'].endswith('.id'):
                option.__getattribute__('attributes').update({'_selected':'selected'})
                id_input_field = grid.element('div#w2p_field_t_status_article-id')
                id_input_field.__getattribute__('attributes').update({'_style':'display:flex'})                
    else:
        # for all other cases, hide the (initially primary) field options, because now "All fields" is primary
        panel_query_rows[1].__getattribute__('attributes').update({'_style':'display:none'})

    for selector in regulator_panels:
        options = selector.elements('option')
        contains_field_set = False
        for option in options:
            if option.__getattribute__('attributes')['_value'] == 'contains':
                option.__getattribute__('attributes').update({'_selected':'selected'})
                contains_field_set = True
                #selector.__getattribute__('attributes').update({'_disabled':'disabled'}) 
            elif option.__getattribute__('attributes')['_value'] == '!=':
                option.__getattribute__('attributes').update({'_class': 'not_contains'})
                selector.elements('option.not_contains', replace=OPTION('not contains', _class="not_contains"))                
            elif option.__getattribute__('attributes')['_value'] in remove_regulators:
                option.__getattribute__('attributes').update({'_style':'display:none'})
        if not contains_field_set:
            for option in options:
                if option.__getattribute__('attributes')['_value'] == '=':
                    option.__getattribute__('attributes').update({'_class': 'contains'})
                    selector.elements('option.contains', replace=OPTION('contains', _class="contains"))                

    grid.elements('div#w2p_query_panel', replace=None)
    grid.elements('div.web2py_breadcrumbs', replace=None)
    grid.elements('div.web2py_console a.btn-secondary', replace=None)

    # change button label from Clear to Reset
    for button in input_buttons:
        if button.__getattribute__('attributes')['_value'] == 'Clear':
            button.__getattribute__('attributes').update({'_value': 'Reset'})

    # add elements at different positions
    grid.element('div.web2py_console ').insert(0, panel)
    if search_name == 'users':
        web2py_grid.insert(0, add_btn)

    return grid

