# Taken and freely adapted from https://github.com/daniel-j/html2latex

from functools import partial
from io import StringIO
from typing import Any, Dict, Optional
import lxml.html
from lxml.cssselect import CSSSelector
import cssutils
import re


hyperlinks: Optional[str] = 'hyperref'
replacements_head: Dict[str, Any] = {}
replacements_tail: Dict[str, Any] = {}


def s(start: str = '', end: str = '', ignoreStyle: bool = False, ignoreContent: bool = False):
    return {
        'start': start,
        'end': end,
        'ignoreStyle': ignoreStyle,
        'ignoreContent': ignoreContent
    }


def handle_anchor(selector: ..., el: ...):
    href = el.get('href')
    name = el.get('name')

    if hyperlinks == 'hyperref':
        start = ''
        end = ''
        if href and href.startswith('#'):
            start = '\\hyperlink{' + href[1:] + '}{'
            end = '}'
        elif name:
            start = '\\hypertarget{' + name + '}{'
            end = '}'
        elif href:
            start = '\\href{' + href + '}{'
            end = '}'
        return s(start, end)
    elif hyperlinks == 'footnotes':
        if href and not href.startswith('#'):
            return s(end='\\footnote{' + href + '}')
    return None


def handle_paragraph(selector: ..., el: ...):
    # hanging indentation
    match = r'^“'
    node = el
    while True:
        if node.text and re.match(match, node.text):
            replacements_head[node] = (match, '\\\\leavevmode\\\\llap{“}')
            break
        elif not node.text and node.__len__() > 0:
            node = node[0]
        else:
            break

    return s('\n\n')


class HtmlToLatex:        

    _selectors: Dict[str, Any] = {
        #'html': s('\\thispagestyle{empty}\n{\n', '\n}\n'),
        'head': s(ignoreContent=True, ignoreStyle=True),
        #'body': s('\n\n', '\n\n\\clearpage\n\n'),
        'blockquote': s('\n\\begin{quotation}', '\n\\end{quotation}'),
        'ol': s('\n\\begin{enumerate}', '\n\\end{enumerate}'),
        'ul': s('\n\\begin{itemize}', '\n\\end{itemize}'),
        'li': s('\n\t\\item '),
        'i': s('\\textit{', '}', ignoreStyle=True),
        'b, strong': s('\\textbf{', '}', ignoreStyle=True),
        'em': s('\\emph{', '}', ignoreStyle=True),
        'u': s('\\underline{', '}', ignoreStyle=True),
        'sub': s('\\textsubscript{', '}'),
        'sup': s('\\textsuperscript{', '}'),
        'br': s('~\\\\\n'),
        'hr': s('\n\n\\line(1,0){300}\n', ignoreStyle=True),
        'a': handle_anchor,

        'p': handle_paragraph,
        '.chapter-name': s('\n\\noindent\\hfil\\charscale[2,0,-0.1\\nbs]{', '}\\hfil\\newline\n\\vspace*{2\\nbs}\n\n', ignoreStyle=True),
        '.chapter-number': s('\\vspace*{3\\nbs}\n\\noindent\\hfil\\charscale[1.0,0,-0.1\\nbs]{\\textsc{\\addfontfeature{Ligatures=NoCommon,LetterSpace=15}{\\strreplace{', '}{ }{}}}}\\hfil\\newline\n\\vspace*{0.0\\nbs}\n', ignoreStyle=True),
        'p.break': s('\n\n\\scenepause', ignoreStyle=True, ignoreContent=True),
        '.center': s('\n\n{\\csname @flushglue\\endcsname=0pt plus .25\\textwidth\n\\noindent\\centering{}', '\\par\n}', ignoreStyle=True)}

    _characters: Dict[str, str] = {
        u'\u00A0': '~',  # &nbsp;
        u'\u2009': '\\,',  # &thinsp;
        u'\u2003': '\\hspace*{1em}',  # &emsp;
        '[': '{[}',
        ']': '{]}'
    }

    _styles: Dict[str, Any] = {
        # defaults
        'font-weight': {
            'bold': ('\\textbf{', '}'),
            'bolder': ('\\textbf{', '}')
        },
        'font-style': {
            'italic': ('\\textit{', '}')
        },
        'font-variant': {
            'small-caps': ('\\textsc{', '}')
        },
        'text-indent': {
            '0': ('\\noindent{}', ''),
            '-1em': ('\\noindent\\hspace*{-1em}', '')
        },
        'text-align': {
            'left': ('\n{\\raggedright{}', '}'),
            'center': ('\n{\\centering{}', '\\par}'),
            'right': ('\n{\\raggedleft{}', '}')
        },
        'text-wrap': {
            'balanced': ('{\\csname @flushglue\\endcsname=0pt plus .25\\textwidth\n', '\n}')
        },
        '-latex-needspace': {
            '2': ('\n\n\\needspace{2\\baselineskip}\n', '')
        },

        'display': {
            'none': s(ignoreContent=True, ignoreStyle=True)
        },

        # customized
        'margin': {
            '0 2em': ('\n\n\\begin{adjustwidth}{2em}{2em}\n', '\n\\end{adjustwidth}\n\n'),
            '0 1em 0 2em': ('\n\n\\begin{adjustwidth}{2em}{1em}\n', '\n\\end{adjustwidth}\n\n'),
            '0 1em': ('\n\n\\begin{adjustwidth}{2em}{2em}\n', '\n\\end{adjustwidth}\n\n')
        },
        'margin-top': {
            '1em': ('\n\n\\vspace{\\baselineskip}\n\\noindent\n', '')
        },
        'margin-bottom': {
            '1em': ('', '\n\n\\vspace{\\baselineskip}\n\\noindent\n')
        },
        '-latex-display': {
            'none': s(ignoreContent=True, ignoreStyle=True)
        }
    }


    def __init__(self):
        self.replacements_head = replacements_head
        self.replacements_tail = replacements_tail


    def convert(self, html: str):
        if len(html) == 0:
            return ''
        
        html_parser = lxml.html.HTMLParser(encoding='utf-8', remove_comments=True)
        tree: ... = lxml.html.parse(StringIO(html), parser=html_parser) # type: ignore
        root = tree.getroot() 
        selectors = self._get_selectors(root, self._selectors)
        out = self._element_to_latex(root, {}, selectors)
        out = re.sub(r"^\s+|\s+$", "", out, flags=re.UNICODE)
        return out


    def _element_to_latex(self, el: ..., cascading_style: Dict[str, Any] = {}, selectors: Dict[str, Any] = {}):
        result: list[str] = []
        heads: list[Any] = []
        tails: list[Any] = []

        # and add inline @style if present
        inlinestyle = self._styleattribute(el)
        if inlinestyle:
            for p in inlinestyle:
                if el not in cascading_style:
                    # add initial empty style declatation
                    cascading_style[el] = cssutils.css.CSSStyleDeclaration()
                # set inline style specificity
                cascading_style[el].setProperty(p)
                # specificities[el][p.name] = (1,0,0,0)

        declarations = cascading_style.get(el, [])

        ignoreContent = False
        ignoreStyle = False
        leaveText = False

        sel = selectors.get(el, None)
        if sel:
            ignoreContent = sel.get('ignoreContent', ignoreContent)
            ignoreStyle = sel.get('ignoreStyle', ignoreStyle)
            leaveText = sel.get('leaveText', leaveText)

        if not ignoreStyle:
            for d in declarations:
                style: Any = self._styles.get(d.name.lower(), None)
                if style:
                    if callable(style):
                        style = style(d.name.lower(), d.value, el)
                    else:
                        style = style.get(d.value, None)
                        if callable(style):
                            style = style(d.name.lower(), d.value, el)
                    if style:
                        if type(style) is tuple:
                            heads.append(style[0])
                            tails.insert(0, style[1])
                        else:
                            heads.append(style.get('start', ''))
                            tails.insert(0, style.get('end', ''))
                            ignoreContent = style.get('ignoreContent', ignoreContent)
                            ignoreStyle = style.get('ignoreStyle', ignoreStyle)
                            leaveText = style.get('leaveText', leaveText)

        if ignoreStyle:
            heads.clear()
            tails.clear()
        if sel:
            heads.insert(0, sel.get('start', ''))
            tails.append(sel.get('end', ''))

        result.append(''.join(heads))

        if not ignoreContent:
            if el.text:
                text: Any = self._inside_characters(el, el.text, leaveText, ignoreContent)
                r = self.replacements_head.get(el, None)
                if r:
                    text = re.sub(r[0], r[1], text)
                result.append(text)
            for child in el:
                result.append(self._element_to_latex(child, cascading_style, selectors))
                if child.tail:
                    text = self._modify_characters(child, child.tail)
                    r = self.replacements_tail.get(el, None)
                    if r:
                        text = re.sub(r[0], r[1], text)
                    result.append(text)

        result.append(''.join(tails))
        result_str = ''.join(result)
        result_str = self._fix_long_url(result_str)

        # strip whitespace at the start and end of lines
        return '\n'.join(map(str.strip, result_str.split('\n')))
    

    def _fix_long_url(self, latex_code: str):
        if latex_code.count("\\href{") != 1 or latex_code.count("\\url{") > 0:
            return latex_code
        
        regex = r"\\href{.*}{(.*)(?P<url>https?://?\w+\.\S*[^.,;?!:<>{}\[\]()\"'\s])}+"
        pattern = re.compile(regex)
        match = pattern.search(latex_code)

        if not match:
            return latex_code
        
        url_label = match.group('url')
        if not url_label:
            return latex_code
        
        new_url_label = f"\\url{{{url_label}}}"

        latex_code = re.sub(pattern, partial(self._replace_closure, 'url', new_url_label), latex_code)
        return latex_code    
    

    def _replace_closure(self, subgroup: str, replacement: str, m: ...):
        start = m.start(subgroup)
        end = m.end(subgroup)
        return str(m.group()[:start] + replacement + m.group()[end:])
    

    def _modify_characters(self, el: ..., string: str, leaveText: bool = False):
        if not leaveText:
            string = string.replace('\n', ' ').replace('\t', ' ')
            string = re.sub('[ ]+', ' ', string)

        if 'math-tex' not in el.attrib.get('class', ''):
            string = self._convert_LaTeX_special_chars(string)
        else:
            string = self._fix_math_annotation(string)
        
        s = list(string)
        for i, char in enumerate(s):
            if char in self._characters:
                s[i] = self._characters.get(char, '')
                if callable(s[i]):
                    s[i] = s[i](el, i, char) # type: ignore
        return ''.join(s)


    def _inside_characters(self, el: ..., string: str, leaveText: bool = False, ignoreContent: bool = False):
        string = self._modify_characters(el, string, leaveText)
        if string.strip() == '' or ignoreContent:
            return ''
        return string
    

    def _convert_LaTeX_special_chars(self, string: str):
        string = string \
            .replace("&#", "&@-HASH-") \
            .replace("{", "\\{").replace("}", "\\}") \
            .replace("\\", "\\textbackslash{}") \
            .replace("$", "\\$").replace("#", "\\#") \
            .replace("%", "\\%").replace("~", "\\textasciitilde{}") \
            .replace("_", "\\_").replace("^", "\\textasciicircum{}") \
            .replace("@-HASH-", "#").replace("&", "\\&")
        return string


    def _fix_math_annotation(self, string: str):
        string = re.sub(r"\\\(\s*\\begin{equation}", r"\\begin{equation}", string)
        string = re.sub(r"\\end\{equation\}\s*\\\)", r"\\end{equation}", string)
        string = re.sub(r"\\\(|\\\)", "$", string)
        return string


    def _styleattribute(self, element: ...):
        value = element.get('style')
        if value:
            return cssutils.css.CSSStyleDeclaration(cssText=value)
        else:
            return None


    def _get_selectors(self, document: Any, selectors: Any):
        view: dict[Any, Any] = {}
        for selector in selectors:
            val = selectors.get(selector)
            cssselector = CSSSelector(selector)
            matching: Any = cssselector.evaluate(document) # type: ignore
            # print(selector, info)
            for element in matching:
                info = val
                if callable(val):
                    info = val(selector, element)
                if element not in view:
                    view[element] = {}
                    if info:
                        view[element].update(info)
                else:
                    if info:
                        view[element].update(info)
        return view
