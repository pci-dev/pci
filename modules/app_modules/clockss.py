from io import StringIO
import os
import ftplib
import pathlib
import shutil
from typing import Any, Dict, List, Optional
from app_components.ongoing_recommendation import getRecommendationProcess
from app_modules.html_to_latex import HtmlToLatex
from app_modules.common_small_html import build_citation, mkSimpleDOI
from models.article import Article
import zipfile as z
from models.recommendation import Recommendation
from app_modules import crossref
from app_modules import common_tools
from gluon.contrib.appconfig import AppConfig
from gluon import current
from models.review import Review
import lxml.html
import lxml.etree


myconf = AppConfig(reload=True)


class Clockss:

    CLOCKSS_SERVER = str(myconf.take("clockss.server"))
    CLOCKSS_USERNAME = str(myconf.take("clockss.username"))
    CLOCKSS_PASSWORD = str(myconf.take("clockss.password")) 

    LATEX_TEMPLATE_FILENAME = 'main.tex'
    PDFLATEX_BIN = str(myconf.take("latex.pdflatex"))
    
    _article: Article
    _prefix: str
    _recommendation: Recommendation
    _html_to_latex: HtmlToLatex

    attachments_dir: str

    def __init__(self, article: Article):
        self._article = article
        self._html_to_latex = HtmlToLatex()
        self._init_dir()
        recommendation = Article.get_last_recommendation(self._article.id)
        if not recommendation:
            raise Exception(f'No recommendation found for article with id: {self._article.id}')
        self._recommendation = recommendation


    def _build_xml(self):
        filename = f"{self.attachments_dir}/{self._prefix}.xml"
        crossref.init_conf(current.db)
        recommendation_xml = crossref.crossref_xml(self._recommendation)
        with open(filename, 'wb') as file:
            file.write(recommendation_xml.encode('utf8'))


    def _init_dir(self):
        prefix = common_tools.generate_recommendation_doi(self._article.id)[9:]
        attachments_dir = os.path.join(str(current.request.folder), "clockss", prefix)
        os.makedirs(attachments_dir, exist_ok=True)
        self._prefix = prefix
        self.attachments_dir = attachments_dir


    def build_pdf(self):
        pdf_path_to_generate = f"{self.attachments_dir}/{self._prefix}.pdf"
        latex_content = self._build_latex_content_from_template()
        if latex_content:
            self._compile_latex(latex_content, pdf_path_to_generate)

        return f"{self._prefix}.pdf"
        

    def _compile_latex(self, latex_content: str, pdf_dest_path: str):
        tmp_folder = f"{current.request.folder}/tmp/{self._prefix}"
        if os.path.exists(tmp_folder):
            shutil.rmtree(tmp_folder)

        shutil.copytree(self._get_templates_dir(), tmp_folder)

        latex_file_path = f"{tmp_folder}/{self._prefix}.tex"
        print(latex_content, file=open(latex_file_path, 'w', encoding='utf-8'))

        os.system(f'{self.PDFLATEX_BIN} --output-directory={tmp_folder} -interaction=nonstopmode {latex_file_path}')
        shutil.move(f"{tmp_folder}/{self._prefix}.pdf", pdf_dest_path)
        shutil.rmtree(tmp_folder)


    def _build_latex_content_from_template(self):
        template = self._get_latex_template_content()

        simple_variables: Dict[str, Any] = {
            'ARTICLE_AUTHORS': self._article.authors,
            'ARTICLE_ABSTRACT': self._article.abstract,
            'ARTICLE_YEAR': self._article.article_year,
            'ARTICLE_VERSION': self._article.ms_version,
            'ARTICLE_COVER_LETTER': self._article.cover_letter,
            'RECOMMENDER_NAMES': Recommendation.get_recommenders_names(self._recommendation),
            'REVIEWER_NAMES': Review.get_reviewers_name(self._article.id),
            'RECOMMENDATION_TITLE': self._recommendation.recommendation_title,
            'RECOMMENDATION_DOI': mkSimpleDOI(self._recommendation.doi),
            'RECOMMENDATION_DOI_ID': Recommendation.get_doi_id(self._recommendation),
            'PCI_NAME': str(myconf.take("app.longname")),
            'PCI_COMMAND': str(myconf.take("app.description")),
            'RECOMMENDATION_CITATION': build_citation(self._article, self._recommendation, False),
        }

        for variable_name, variable_value in simple_variables.items():
            template = self._replace_var_in_template(variable_name, variable_value, template)

        template = self._replace_list_references_in_template('ARTICLE_DATA_DOI', template)
        template = self._replace_recommendation_process('RECOMMENDATION_PROCESS', template)

        return template
    

    def _replace_recommendation_process(self, var_title: str, template: str):
        recommendation_process: Any = getRecommendationProcess(current.auth, current.db, current.response, self._article)
        recommendation_process = recommendation_process.components[0]
        latex_code: List[str] = []
        for round in recommendation_process.components:
            if not round:
                continue

            html_parser = lxml.html.HTMLParser(encoding='utf-8', remove_comments=True)
            tree: ... = lxml.html.parse(StringIO(str(round)), parser=html_parser) # type: ignore
            root = tree.getroot()

            round_number = root.xpath('//h2[@class="pci2-revision-round-title"]//b[@class="pci2-main-color-text"]/text()')
            if round_number and len(round_number) > 0:
                round_number = round_number[0].replace('#', '')
                latex_code.append(f"\\subsection*{{Round {round_number}}}")
            else:
                continue

            author_reply = root.xpath('//h4[@id="author-reply"]/following-sibling::div/div')
            if author_reply and len(author_reply) > 0:
                author_reply: ... = lxml.html.tostring(author_reply[0]).decode('utf-8') # type: ignore
                author_reply = self._html_to_latex.convert(author_reply)
                latex_code.append(f"\\subsubsection*{{Authors' response}}")
                latex_code.append(f"{author_reply}")
            
            recommender_decision = root.xpath('//div[@class="pci2-recomm-text"]')
            if recommender_decision and len(recommender_decision) > 0:
                recommender_decision: ... = lxml.html.tostring(recommender_decision[0]).decode('utf-8') # type: ignore
                recommender_decision = self._html_to_latex.convert(recommender_decision)
                latex_code.append(f"\\subsubsection*{{Decision by {{\\recommender}}}}")
                latex_code.append(recommender_decision)

            reviews = root.xpath('//div[@class="review"]')
            if len(reviews) > 0:
                latex_code.append("\\subsubsection*{{Reviews}}")
                
            for review in reviews:
                review_author = review.xpath('h4/span/text()')
                if review_author and len(review_author) > 0:
                    review_author = str(review_author[0]).split(',')[0]
                else:
                    continue

                review_content = review.xpath('div')
                if review_content and len(review_content) > 0:
                    review_content: ... = lxml.html.tostring(review_content[0]).decode('utf-8') # type: ignore
                    review_content = self._html_to_latex.convert(review_content)
                    latex_code.append(f"\\subsubsection*{{Review by {review_author}}}")
                    latex_code.append(review_content)
            
        return template.replace(f"[[{var_title.upper()}]]", "\n".join(latex_code))


    def _replace_var_in_template(self, var_title: str, var_content: Optional[Any], template: str, latex_format: bool = False):
        content = str(var_content) or f"Missing {var_title.lower()}"
        if not latex_format:
            content = self._html_to_latex.convert(content)
        return template.replace(f"[[{var_title.upper()}]]", content)
    

    def _replace_list_references_in_template(self, var_title: str, template: str):
        references: List[str] = []
        if self._article.data_doi and len(self._article.data_doi) > 0:
            references.extend(self._article.data_doi)
        if self._recommendation.recommendation_comments:
            references.extend(common_tools.get_urls_in_string(self._recommendation.recommendation_comments))

        if len(references) == 0:
            return self._replace_var_in_template(var_title, 'No references', template)
        
        i = 1
        content: List[str] = [r'\begin{itemize}']
        for reference in references:
            content.append(f"\\item[]{{}}[{i}] \\url{{{reference}}}")
            i += 1
        content.append(r'\end{itemize}')
        return self._replace_var_in_template(var_title, '\n'.join(content), template, True)


    def _get_latex_template_content(self):
        template_path = f"{self._get_templates_dir()}{self.LATEX_TEMPLATE_FILENAME}"
        with open(template_path, 'r') as template:
            return template.read()
        
    
    def _get_templates_dir(self):
        return f"{current.request.folder}/templates/clockss/"


    def _zip_directory(self, filepath: str):
        direc = pathlib.Path(filepath)
        with z.ZipFile(f'{filepath}.zip', 'w', z.ZIP_DEFLATED) as zp:
            for file in direc.iterdir():
                zp.write(file, arcname=file.name)


    def compile_and_send(self):
        ftp_server = self._clokss_ftp()
        if ftp_server is None:
            raise Exception('Missing Clockss FTP configuration')

        self._build_xml()
        self._zip_directory(self.attachments_dir)
        filename = self.attachments_dir + ".zip"
        with open(filename, 'rb') as file:
            try:
                ftp_server.storbinary(f'STOR {self._prefix}.zip', file)
            finally:
                ftp_server.quit()

        #delete files after upload
        shutil.rmtree(self.attachments_dir)
        os.remove(filename)

    def _clokss_ftp(self):
        if self.CLOCKSS_SERVER and self.CLOCKSS_USERNAME and self.CLOCKSS_PASSWORD:
            return ftplib.FTP(self.CLOCKSS_SERVER, self.CLOCKSS_USERNAME, self.CLOCKSS_PASSWORD)
