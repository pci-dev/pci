# -*- coding: utf-8 -*-
from app_modules.helper import OPTION, TR, TD
from app_modules import common_small_html
import re


remove_regulators = ['=', '<=', '!=', '<', '>', '>=', 'starts with', 'in', 'not in']
search_name2field = {'reviewers': 'auth_user', 'users': 'auth_user',
                     'recommenders': 'auth_user', 'recommenders2': 'qy_recomm', 'articles': 't_articles', 'articles_temp': 't_articles',
                     'articles2': 't_status_article', 'mail_queue': 'mail_queue', 'recommenders_about' : 'auth_user',
                     'main_articles': 'qy_articles', 'help_texts': 'help_texts'}

def adjust_grid_basic(grid, search_name, remove_options = [], integer_fields = []):
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
    panel.attributes.update({'_style':'display:flex'})
    if search_name == 'templates':
        panel_search_field = grid.element('div#w2p_field_mail_templates-lang')
    elif search_name == 'users':
        panel_search_field = grid.element('div#w2p_field_auth_user-id')
        panel_search_field.attributes.update({'_style':'display:flex'})
        # restyle the add button
        add_btn = grid.element('div.web2py_console a.btn-secondary')
        add_btn.attributes.update({'_style':'margin-bottom:4rem'})
    elif search_name in ['recommenders', 'recommenders_about']:
        panel_search_field = grid.element('div#w2p_field_auth_user-first_name')
        panel_search_field.attributes.update({'_style':'display:flex'})
    elif search_name == 'articles':
        panel_search_field = grid.element('div#w2p_field_t_articles-id')
        panel_search_field.attributes.update({'_style':'display:flex'})
    elif search_name == 'articles_temp':
        panel_search_field = grid.element('div#w2p_field_t_articles-title')
        panel_search_field.attributes.update({'_style':'display:flex'})
    elif search_name == 'articles2':
        panel_search_field = grid.element('div#w2p_field_qy_art-id')
        panel_search_field.attributes.update({'_style':'display:flex'})
    elif search_name == 'main_articles':
        panel_search_field = grid.element('div#w2p_field_v_article-title')
        panel_search_field.attributes.update({'_style':'display:flex'})
    elif search_name == 'mail_queue':
        panel_search_field = grid.element('div#w2p_field_mail_queue-sending_status')
        panel_search_field.attributes.update({'_style':'display:flex'})
    elif search_name == 'help_texts':
        panel_search_field = grid.element('div#w2p_field_help_texts-hashtag')
        panel_search_field.attributes.update({'_style':'display:flex'})

    # restyle Add, And, Or, Close buttons
    for btn in btns:
        if btn.attributes['_value'] == 'New Search':
            btn.attributes.update({'_class':'btn btn-default add-btn'})
        elif btn.attributes['_value'] == '+ And':
            btn.attributes.update({'_style':'display:none'})
            btn.attributes.update({'_class':'btn btn-default and-btn'})
        elif btn.attributes['_value'] == '+ Or':
            btn.attributes.update({'_style':'display:none'})
            btn.attributes.update({'_class':'btn btn-default or-btn'})
        elif btn.attributes['_value'] == 'Close':
            btn.attributes.update({'_style':'display:none'})

    # initially, the ADD buttons are now green SEARCH buttons
    add_btns = grid.elements('div#w2p_query_panel input.add-btn')
    for ab in add_btns:
        ab.attributes.update({'_value':'SEARCH'})
        ab.attributes.update({'_style':'background-color:#93c54b'})
        ab.attributes.update({'_onclick':'new_search(this)'})

    # initially, the large search field is hidden
    search_field.attributes.update({'_style': 'display:none'})

    # remove options, regulators, and other elements that are not required;
    # also add integer CSS to mark integer fields
    for option in select_panel:
        if option.attributes['_value'].endswith('any'):
            option.attributes.update({'_class':'selector'})
            grid.element('div#w2p_field_' + search_name2field[search_name] + '-any').attributes.update({'_style':'display:flex'})
        # remove the fields that are not required
        elif option.attributes['_value'] in remove_options:
            option.attributes.update({'_style':'display:none'})
            grid.elements('div#w2p_field_' + option.attributes['_value'].replace('.', '-'), replace=None)
        elif option.attributes['_value'] in integer_fields:
            option.attributes.update({'_class':'integer-field'})

    # set "All Fields" as primary choice
    for option in select_panel:
        if option.attributes['_value'].endswith('.any'):
            option.attributes.update({'_selected':'selected'})

    # in list_users(), where we have no "All fields", set "First name" as primary choice.
    # similarly, in mail_templates we set "Hashtag" as primary choice.
    if search_name in ['users', 'reviewers', 'recommenders']:
        for option in select_panel:
            if option.attributes['_value'].endswith('.first_name'):
                option.attributes.update({'_selected':'selected'})
                first_name_input_field = grid.element('div#w2p_field_auth_user-first_name')
                first_name_input_field.attributes.update({'_style':'display:flex'})
    elif search_name == 'templates':
        for option in select_panel:
            if option.attributes['_value'].endswith('.hashtag'):
                option.attributes.update({'_selected':'selected'})
                hashtag_input_field = grid.element('div#w2p_field_mail_templates-hashtag')
                hashtag_input_field.attributes.update({'_style':'display:flex'})
    elif search_name in ['articles', 'articles_temp']:
        for option in select_panel:
            if option.attributes['_value'].endswith('.title'):
                option.attributes.update({'_selected':'selected'})
                title_input_field = grid.element('div#w2p_field_t_articles-title')
                title_input_field.attributes.update({'_style':'display:flex'})
    elif search_name == 'articles2':
        for option in select_panel:
            if option.attributes['_value'].endswith('.text'):
                option.attributes.update({'_selected':'selected'})
                id_input_field = grid.element('div#w2p_field_qy_art-text')
                id_input_field.attributes.update({'_style':'display:flex'})
    elif search_name == 'main_articles':
        for option in select_panel:
            if option.attributes['_value'].endswith('.title'):
                option.attributes.update({'_selected':'selected'})
                title_input_field = grid.element('div#w2p_field_v_article-title')
                title_input_field.attributes.update({'_style':'display:flex'})                
    elif search_name == 'mail_queue':
        for option in select_panel:
            if option.attributes['_value'].endswith('.sending_status'):
                option.attributes.update({'_selected':'selected'})
                sending_status_input_field = grid.element('div#w2p_field_mail_queue-sending_status')
                sending_status_input_field.attributes.update({'_style':'display:flex'})
    elif search_name == 'help_texts':
        for option in select_panel:
            if option.attributes['_value'].endswith('.hashtag'):
                option.attributes.update({'_selected':'selected'})
                sending_status_input_field = grid.element('div#w2p_field_help_texts-hashtag')
                sending_status_input_field.attributes.update({'_style':'display:flex'})
    elif search_name == 'recommenders_about':
        for option in select_panel:
            if option.attributes['_value'].endswith('.first_name'):
                option.attributes.update({'_selected':'selected'})
                first_name_input_field = grid.element('div#w2p_field_auth_user-first_name')
                first_name_input_field.attributes.update({'_style':'display:flex'})
                option.__setitem__(0,'First Name')
            elif option.attributes['_value'].endswith('.institution'):
                option.__setitem__(0,'Institution')
    else:
        # for all other cases, hide the (initially primary) field options, because now "All fields" is primary
        panel_query_rows[1].attributes.update({'_style':'display:none'})

    for selector in regulator_panels:
        options = selector.elements('option')
        contains_field_set = False
        for option in options:
            if option.attributes['_value'] == 'contains':
                option.attributes.update({'_selected':'selected'})
                contains_field_set = True
            elif option.attributes['_value'] == '!=':
                option.attributes.update({'_class': 'not_contains'})
                selector.elements('option.not_contains', replace=OPTION('not contains', _class="not_contains"))                
            elif option.attributes['_value'] in remove_regulators:
                option.attributes.update({'_style':'display:none'})
        if not contains_field_set:
            for option in options:
                if option.attributes['_value'] == '=':
                    option.attributes.update({'_class': 'contains'})
                    selector.elements('option.contains', replace=OPTION('contains', _class="contains"))                

    grid.elements('div#w2p_query_panel', replace=None)
    grid.elements('div.web2py_breadcrumbs', replace=None)
    grid.elements('div.web2py_console a.btn-secondary', replace=None)

    # change button label from Clear to Reset
    for button in input_buttons:
        if button.attributes['_value'] == 'Clear':
            button.attributes.update({'_value': 'Reset'})

    # add elements at different positions
    grid.element('div.web2py_console ').insert(0, panel)
    if search_name == 'users':
        web2py_grid.insert(0, add_btn)

    # default search to simple = hide advanced search console
    grid.element('div.web2py_console ').attributes.update({'_style': 'display:none'})
    
    alphabetical_search_widget(search_name, grid, web2py_grid)

    return grid


def alphabetical_search_widget(search_name, grid, web2py_grid):
    '''
    creates the alphabetical search widget for about/recommenders
    '''
    # for the about/recommenders page, we introduce the character search widget
    if search_name == 'recommenders_about':
        markdown = lambda text,tag=None,attributes={}: {None: re.sub('\s+',' ',text), 'a':text+'\n\n'}.get(tag,text)
        chars = []
        result_table = grid.element('div.web2py_htmltable')
        if result_table:
            result_body = result_table.elements('tbody')[0]
            result_table_rows = result_table.elements('tr')

            # iterate over rows to...
            if len(result_table_rows) > 1:
                for i,row in enumerate(result_table_rows):
                    columns_a = row.elements('td a')
                    # ...create table rows with upper letters
                    for c in columns_a:
                        name = c.flatten(markdown)
                        first_char = name.upper().split(' ')[1:][0][0]
                        char_row = TR( TD(first_char, _id=first_char), TD(), _class="pci-capitals",)
                        if first_char not in chars:
                            result_body.insert(i-1+len(chars), char_row)
                            chars.append(first_char)
                        break

            # Finally, fetch the search widget
            if len(chars) > 0:
                search_widget = common_small_html.mkSearchWidget(chars)
                web2py_grid.insert(1, search_widget)
