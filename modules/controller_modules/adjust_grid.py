# -*- coding: utf-8 -*-
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse
from app_modules.helper import OPTION, TR, TD
from app_modules import common_small_html
import re

from gluon import A, TABLE


remove_regulators = ['=', '<=', '!=', '<', '>', '>=', 'starts with', 'in', 'not in']
search_name2field = {'reviewers': 'auth_user', 'users': 'auth_user',
                     'recommenders': 'auth_user', 'recommenders2': 'qy_recomm', 'articles': 't_articles', 'articles_temp': 't_articles',
                     'articles2': 't_status_article', 'mail_queue': 'mail_queue', 'recommenders_about' : 'auth_user',
                     'main_articles': 'qy_articles', 'help_texts': 'help_texts'}

class LazyGridElement:

    _grid: ...
    _queries: Dict[str, Any]

    def __init__(self, grid: ...):
        self._grid = grid
        self._queries = {}

    def get(self, css: str) -> ...:
        return self._queries.setdefault(css, self._grid.element(css))
    
    def gets(self, css: str) -> ...:
        return self._queries.setdefault(css, self._grid.elements(css))


def adjust_grid_basic(grid: ...,
                      search_name: str,
                      remove_options: List[str] = [],
                      integer_fields: List[str] = [],
                      columns_to_hide: List[str] = []):
    '''
    function that adjusts the grid after its generation
    '''
    el = LazyGridElement(grid)

    # gather elements
    web2py_grid = 'div.web2py_grid'
    panel = 'div#w2p_query_panel'
    btns = 'input.btn-default'
    select_panel = 'select#w2p_query_fields'
    regulator_panels = 'select.form-control'
    search_field = '.web2py_console form'
    panel_query_rows = 'div#w2p_query_panel div'
    input_buttons = 'form input.btn'
    
    add_btn: ... = None

    # individual changes
    el.get(panel).attributes.update({'_style':'display:flex'})
    if search_name == 'templates':
        panel_search_field = el.get('div#w2p_field_mail_templates-lang')
    elif search_name == 'users':
        panel_search_field = el.get('div#w2p_field_auth_user-id')
        panel_search_field.attributes.update({'_style':'display:flex'})
        # restyle the add button
        add_btn = el.get('div.web2py_console a.btn-secondary')
        add_btn.attributes.update({'_style':'margin-bottom:4rem'})
    elif search_name in ['recommenders', 'recommenders_about']:
        panel_search_field = el.get('div#w2p_field_auth_user-first_name')
        panel_search_field.attributes.update({'_style':'display:flex'})
    elif search_name == 'articles':
        panel_search_field = el.get('div#w2p_field_t_articles-id')
        panel_search_field.attributes.update({'_style':'display:flex'})
    elif search_name == 'articles_temp':
        panel_search_field = el.get('div#w2p_field_t_articles-title')
        panel_search_field.attributes.update({'_style':'display:flex'})
    elif search_name == 'articles2':
        panel_search_field = el.get('div#w2p_field_qy_art-id')
        panel_search_field.attributes.update({'_style':'display:flex'})
    elif search_name == 'main_articles':
        panel_search_field = el.get('div#w2p_field_v_article-title')
        panel_search_field.attributes.update({'_style':'display:flex'})
    elif search_name == 'mail_queue':
        panel_search_field = el.get('div#w2p_field_mail_queue-sending_status')
        panel_search_field.attributes.update({'_style':'display:flex'})
    elif search_name == 'help_texts':
        panel_search_field = el.get('div#w2p_field_help_texts-hashtag')
        panel_search_field.attributes.update({'_style':'display:flex'})

    # restyle Add, And, Or, Close buttons
    for btn in el.gets(btns):
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
    el.get(search_field).attributes.update({'_style': 'display:none'})

    # remove options, regulators, and other elements that are not required;
    # also add integer CSS to mark integer fields
    for option in el.get(select_panel):
        if option.attributes['_value'].endswith('any'):
            option.attributes.update({'_class':'selector'})
            el.get('div#w2p_field_' + search_name2field[search_name] + '-any').attributes.update({'_style':'display:flex'})
        # remove the fields that are not required
        elif option.attributes['_value'] in remove_options:
            option.attributes.update({'_style':'display:none'})
            grid.elements('div#w2p_field_' + option.attributes['_value'].replace('.', '-'), replace=None)
        # add integer class to fields that need to be handled like integer
        elif option.attributes['_value'] in integer_fields:
            option.attributes.update({'_class':'integer-field'})
        # these names of search options need to be adjusted to adhere to the fields they represent
        # (which is differing to the labels in the result table)
        if search_name == 'articles' and option.attributes['_value'] == 't_articles.id':
            option.components[0] = 'Article ID'
        if search_name == 'articles' and option.attributes['_value'] == 't_articles.title':
            option.components[0] = 'Article title'

    # set "All Fields" as primary choice
    for option in el.get(select_panel):
        if option.attributes['_value'].endswith('.any'):
            option.attributes.update({'_selected':'selected'})

    # in list_users(), where we have no "All fields", set "First name" as primary choice.
    # similarly, in mail_templates we set "Hashtag" as primary choice.
    if search_name in ['users', 'reviewers', 'recommenders']:
        for option in el.get(select_panel):
            if option.attributes['_value'].endswith('.first_name'):
                option.attributes.update({'_selected':'selected'})
                first_name_input_field = el.get('div#w2p_field_auth_user-first_name')
                first_name_input_field.attributes.update({'_style':'display:flex'})
    elif search_name == 'templates':
        for option in el.get(select_panel):
            if option.attributes['_value'].endswith('.hashtag'):
                option.attributes.update({'_selected':'selected'})
                hashtag_input_field = el.get('div#w2p_field_mail_templates-hashtag')
                hashtag_input_field.attributes.update({'_style':'display:flex'})
    elif search_name in ['articles_temp']:
        for option in el.get(select_panel):
            if option.attributes['_value'].endswith('.title'):
                option.attributes.update({'_selected':'selected'})
                title_input_field = el.get('div#w2p_field_t_articles-title')
                title_input_field.attributes.update({'_style':'display:flex'})
    elif search_name in ['articles']:
        for option in el.get(select_panel):
            if option.attributes['_value'].endswith('articles.id'):
                option.attributes.update({'_selected':'selected'})
                title_input_field = el.get('div#w2p_field_t_articles-id')
                title_input_field.attributes.update({'_style':'display:flex'})                
    elif search_name == 'articles2':
        for option in el.get(select_panel):
            if option.attributes['_value'].endswith('.text'):
                option.attributes.update({'_selected':'selected'})
                id_input_field = el.get('div#w2p_field_qy_art-text')
                id_input_field.attributes.update({'_style':'display:flex'})
    elif search_name == 'main_articles':
        for option in el.get(select_panel):
            if option.attributes['_value'].endswith('.title'):
                option.attributes.update({'_selected':'selected'})
                title_input_field = el.get('div#w2p_field_v_article-title')
                title_input_field.attributes.update({'_style':'display:flex'})                
    elif search_name == 'mail_queue':
        for option in el.get(select_panel):
            if option.attributes['_value'].endswith('.sending_status'):
                option.attributes.update({'_selected':'selected'})
                sending_status_input_field = el.get('div#w2p_field_mail_queue-sending_status')
                sending_status_input_field.attributes.update({'_style':'display:flex'})
    elif search_name == 'help_texts':
        for option in el.get(select_panel):
            if option.attributes['_value'].endswith('.hashtag'):
                option.attributes.update({'_selected':'selected'})
                sending_status_input_field = el.get('div#w2p_field_help_texts-hashtag')
                sending_status_input_field.attributes.update({'_style':'display:flex'})
    elif search_name == 'recommenders_about':
        for option in el.get(select_panel):
            if option.attributes['_value'].endswith('.first_name'):
                option.attributes.update({'_selected':'selected'})
                first_name_input_field = el.get('div#w2p_field_auth_user-first_name')
                first_name_input_field.attributes.update({'_style':'display:flex'})
                option.__setitem__(0,'First Name')
            elif option.attributes['_value'].endswith('.institution'):
                option.__setitem__(0,'Institution')
    else:
        # for all other cases, hide the (initially primary) field options, because now "All fields" is primary
        el.gets(panel_query_rows)[1].attributes.update({'_style':'display:none'})

    for selector in el.gets(regulator_panels):
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
    for button in el.gets(input_buttons):
        if button.attributes['_value'] == 'Clear':
            button.attributes.update({'_value': 'Reset'})

    # add elements at different positions
    el.get('div.web2py_console ').insert(0, el.get(panel))
    if search_name == 'users':
        el.get(web2py_grid).insert(0, add_btn)

    # default search to simple = hide advanced search console
    el.get('div.web2py_console ').attributes.update({'_style': 'display:none'})

    # for the about/recommenders page, we introduce the character search widget
    if search_name == 'recommenders_about':
        result_table = el.get('div.web2py_htmltable tbody')
        alphabetical_search_widget(result_table, el.get(web2py_grid))

    if columns_to_hide:
        remove_in_table(grid, columns_to_hide)

    return grid


def remove_in_table(grid: ..., columns_to_hide: List[str]):
    table: ... = grid.components[1].components[0].components[0]
    if not isinstance(table, TABLE):
        return

    thead: ... = table.components[1] # type: ignore

    column_index_to_hide: List[int] = []

    for i, th in enumerate(thead.components[0].components):
        link: ... = th.components[0]
        column_id = ''
        if isinstance(link, A):
            column_id = str(link.attributes['_href']) # type: ignore
        else:
            column_id = str(link)

        column_id = parse_qs(urlparse(column_id).query)

        for column in columns_to_hide:
                if column in column_id:
                    column_index_to_hide.append(i)

    for i in column_index_to_hide:
        thead.components[0].components[i].attributes['_style'] = 'display: none;'
        for tr in table.components[2].components: # type: ignore
            tr.components[i].attributes['_style'] = 'display: none;' # type: ignore


def alphabetical_search_widget(result_table: ..., web2py_grid: ...):
    '''
    creates the alphabetical search widget for about/recommenders
    '''
    def markdown_fn(text: str, tag: Optional[str] = None, attributes: Dict[str, str]= {}):
        return {None: re.sub(r'\s+',' ',text), 'a':text}.get(tag,text)

    markdown = markdown_fn
    chars: List[str] = []
    rows: List[Any] = result_table.elements('tr') if result_table else []

    for i,row in enumerate(rows):
        columns_a = row.elements('td a')
        # ...create table rows with upper letters
        for c in columns_a:
            name = c.flatten(markdown)
            name_parts = name.split(' ')
            first_char = ''
            for part in name_parts:
                if part.isupper() and '.' not in part and len(part) > 1:
                    first_char = part[0]
                    break
            char_row = TR( TD(first_char, _id=first_char), TD(), _class="pci-capitals",)
            if first_char not in chars:
                chars.append(first_char)
                result_table.insert(i-1+len(chars), char_row)
            break

    if chars:
        chars.sort()
        search_widget = common_small_html.mkSearchWidget(chars)
        web2py_grid.insert(1, search_widget)
