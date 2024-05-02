from io import StringIO
import os
import ftplib
import pathlib
import shutil
import string
from typing import Any, Dict, List, Optional

from app_components.ongoing_recommendation import getRecommendationProcess
from app_modules.html_to_latex import HtmlToLatex
from app_modules.common_small_html import build_citation, mkSimpleDOI
from configparser import NoOptionError
from models.article import Article
from models.pdf import PDF
from models.review import Review
from models.recommendation import Recommendation
from app_modules import crossref
from app_modules import common_tools

from gluon.html import TAG
from gluon.contrib.appconfig import AppConfig
from gluon import current

import zipfile as z
import lxml.html
import lxml.etree


myconf = AppConfig(reload=True)


class Clockss:

    CLOCKSS_SERVER: Optional[str] = myconf.get("clockss.server")
    CLOCKSS_USERNAME: Optional[str] = myconf.get("clockss.username")
    CLOCKSS_PASSWORD: Optional[str] = myconf.get("clockss.password")

    LATEX_TEMPLATE_FILENAME = 'main.tex'
    PDFLATEX_BIN: Optional[str] = myconf.get("latex.pdflatex")
    
    _article: Article
    _prefix: str
    _pdf_name: str
    _recommendation: Recommendation
    _html_to_latex: HtmlToLatex

    attachments_dir: str

    def __init__(self, article: Article):
        self._article = article
        self._html_to_latex = HtmlToLatex()
        self._init_dir()
        self._pdf_name = f"{self._prefix}.pdf"
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
        pdf_path_to_generate = f"{self.attachments_dir}/{self._pdf_name}"
        latex_content = self._build_latex_content_from_template()
        if latex_content:
            self._compile_latex(latex_content, pdf_path_to_generate)

        return self._pdf_name
        

    def _compile_latex(self, latex_content: str, pdf_dest_path: str):
        if not self.PDFLATEX_BIN:
            raise NoOptionError('pdflatex', 'latex')

        tmp_folder = f"{current.request.folder}/tmp/{self._prefix}"
        if os.path.exists(tmp_folder):
            shutil.rmtree(tmp_folder)

        shutil.copytree(self._get_templates_dir(), tmp_folder)

        latex_file_path = f"{tmp_folder}/{self._prefix}.tex"
        print(latex_content, file=open(latex_file_path, 'w', encoding='utf-8'))

        os.system(f'{self.PDFLATEX_BIN} --output-directory={tmp_folder} -interaction=nonstopmode {latex_file_path}')
        shutil.move(f"{tmp_folder}/{self._pdf_name}", pdf_dest_path)
        shutil.rmtree(tmp_folder)


    def _build_latex_content_from_template(self):
        template = self._get_latex_template_content()

        simple_variables: Dict[str, Any] = {
            'ARTICLE_AUTHORS': self._article.authors,
            'ARTICLE_TITLE': self._article.title,
            'RECOMMENDATION_ABSTRACT': self._remove_references_in_recommendation_decision(self._recommendation.recommendation_comments or ''),
            'ARTICLE_YEAR': self._article.article_year,
            'ARTICLE_VERSION': self._article.ms_version,
            'ARTICLE_COVER_LETTER': self._article.cover_letter,
            'RECOMMENDER_NAMES': Recommendation.get_recommenders_names(self._recommendation),
            'REVIEWER_NAMES': Review.get_reviewers_name(self._article.id),
            'RECOMMENDATION_TITLE': self._recommendation.recommendation_title,
            'RECOMMENDATION_DOI': mkSimpleDOI(self._recommendation.doi),
            'PREPRINT_SERVER': self._article.preprint_server,
            'RECOMMENDATION_CITATION': build_citation(self._article, self._recommendation, True),
            'RECOMMENDATION_VALIDATION_DATE': self._recommendation.validation_timestamp.strftime("%d %B %Y") if self._recommendation.validation_timestamp else None
        }

        for variable_name, variable_value in simple_variables.items():
            template = self._replace_var_in_template(variable_name, variable_value, template)

        template = self._replace_list_references_in_template('ARTICLE_DATA_DOI', template)
        template = self._replace_recommendation_process('RECOMMENDATION_PROCESS', template)
        template = self._replace_img_in_template(template)

        return template
    

    def _replace_img_in_template(self, template: str):
        pci = str(myconf.take("app.description")).lower()
        img_map = {
            'peer community in registered reports': 'logo_PDF_rr.jpg',
            'peer community in zoology': 'logo_PDF_zool.jpg',
            'peer community in ecology': 'logo_PDF_ecology.jpg',
            'peer community in animal science': 'logo_PDF_animsci.jpg',
            'peer community in archaeology': 'logo_PDF_archaeo.jpg',
            'peer community in forest and wood sciences': 'logo_PDF_fws.jpg',
            'peer community in genomics': 'logo_PDF_genomics.jpg',
            'peer community in mathematical and computational biology': 'logo_PDF_mcb.jpg',
            'peer community in network science': 'logo_PDF_networksci.jpg',
            'peer community in paleontology': 'logo_PDF_paleo.jpg',
            'peer community in neuroscience': 'logo_PDF_neuro.jpg',
            'peer community in ecotoxicology and environmental chemistry': 'logo_PDF_ecotoxenvchem.jpg',
            'peer community in infections': 'logo_PDF_infections.jpg',
            'peer community in health and movement sciences': 'logo_PDF_healthandmovementsciences.png',
            'peer community in microbiology': 'logo_PDF_microbiology.png',
            'peer community in organization studies': 'logo_PDF_organizationstudies.png',
            'peer community in computational statistics': 'logo_PDF_computationalstatistics.png'
        }
        img = img_map.get(pci, 'logo_PDF_evolbiol.jpg')
        return self._replace_var_in_template('PCI_IMG', img, template)
    

    def _replace_recommendation_process(self, var_title: str, template: str):
        recommendation_process: Any = getRecommendationProcess(current.auth, current.db, current.response, self._article)
        recommendation_process = recommendation_process.components[0]
        latex_code: List[str] = []
        first_round = True

        for round in recommendation_process.components:
            if not round:
                continue

            html_parser = lxml.html.HTMLParser(encoding='utf-8', remove_comments=True)
            tree: ... = lxml.html.parse(StringIO(str(round)), parser=html_parser) # type: ignore
            root = tree.getroot()
            latex_round: List[str] = []

            round_number: str = root.xpath('//h2[@class="pci2-revision-round-title"]//b[@class="pci2-main-color-text"]/text()')
            if round_number and len(round_number) > 0:
                round_number = round_number[0].replace('#', '')
                latex_round.append(f"\\subsection*{{Round {round_number}}}")
            else:
                continue

            author_reply = root.xpath('//h4[@id="author-reply"]/following-sibling::div/div')
            if author_reply and len(author_reply) > 0:
                author_reply = str(lxml.html.tostring(author_reply[0]).decode('utf-8')) # type: ignore
                author_reply = self._html_to_latex.convert(author_reply)
                latex_round.append(f"\\subsubsection*{{Authors' response}}")
                latex_round.append(f"{author_reply}")
            
            recommender_decision = root.xpath('//div[@class="pci2-recomm-text"]')
            if recommender_decision and len(recommender_decision) > 0 and not first_round:
                recommender_decision = str(lxml.html.tostring(recommender_decision[0]).decode('utf-8')) # type: ignore
                recommender_decision = self._remove_references_in_recommendation_decision(recommender_decision)
                recommender_decision = self._html_to_latex.convert(recommender_decision)
                latex_round.append(f"\\subsubsection*{{Decision by {{\\recommender}}}}")
                latex_round.append(recommender_decision)

            reviews = root.xpath('//div[@class="review"]')
            if len(reviews) > 0:
                latex_round.append("\\subsubsection*{{Reviews}}")
                
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
                    latex_round.append(f"\\subsubsection*{{Review by {review_author}}}")
                    latex_round.append(review_content)
            
            if len(latex_round) > 1:
                latex_code.extend(latex_round)
                
            first_round = False

        return template.replace(f"[[{var_title.upper()}]]", "\n".join(latex_code))


    def _remove_references_in_recommendation_decision(self, recommendation_decision: str):
        recommendation_comments = recommendation_decision
        recommendation_text: List[str] = []

        lines = recommendation_comments.splitlines()
        for line in lines:
            try:
                line_text = str(TAG(line).flatten().lower().strip()) # type: ignore
            except:
                line_text = line
            line_text = line_text.translate(str.maketrans('', '', string.punctuation))

            if line_text in ['reference', 'references']:
                break
            
            recommendation_text.append(line)

        return '\n'.join(recommendation_text)
    

    def _replace_var_in_template(self, var_title: str, var_content: Optional[Any], template: str, latex_format: bool = False):
        content = str(var_content) or f"Missing {var_title.lower()}"
        if not latex_format:
            content = self._html_to_latex.convert(content)
        return template.replace(f"[[{var_title.upper()}]]", content)
    

    def _replace_list_references_in_template(self, var_title: str, template: str):
        references: List[str] = Recommendation.get_references(self._recommendation)

        if len(references) == 0:
            return self._replace_var_in_template(var_title, 'No references', template)
        
        i = 1
        content: List[str] = [r'\begin{itemize}']
        for reference in references:
            reference = self._html_to_latex.convert(reference)
            content.append(f"\\item[]{{}}[{i}] {reference}")
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


    def package_and_send(self):
        ftp_server = self._clockss_ftp()
        if ftp_server is None:
            raise NoOptionError('server/username/password', 'clockss')

        self._build_xml()
        self._zip_directory(self.attachments_dir)
        filename = self.attachments_dir + ".zip"
        with open(filename, 'rb') as file:
            try:
                ftp_server.storbinary(f'STOR {self._prefix}.zip', file)
            finally:
                ftp_server.quit()

        # delete files after upload
        shutil.rmtree(self.attachments_dir)
        os.remove(filename)


    def _clockss_ftp(self):
        if self.CLOCKSS_SERVER and self.CLOCKSS_USERNAME and self.CLOCKSS_PASSWORD:
            host, port = (self.CLOCKSS_SERVER + ":21").split(":")[:2]
            ftplib.FTP_PORT = int(port)
            return ftplib.FTP(host, self.CLOCKSS_USERNAME, self.CLOCKSS_PASSWORD)


def send_to_clockss(article: Article, recommendation: Recommendation):
    clockss = Clockss(article)
    attachments_dir= clockss.attachments_dir
    try:
        filename = clockss.build_pdf()
    except Exception as e:
        current.session.flash = f"Error building Clockss PDF: {e}"
        return
    try:
        PDF.save_pdf_to_db(recommendation, attachments_dir, filename)
        clockss.package_and_send()
    except NoOptionError:
        PDF.delete_pdf_to_db(recommendation.id)
    except Exception as e:
        current.session.flash = f"Error to upload to Clockss: {e}"
        PDF.delete_pdf_to_db(recommendation.id)
