import os
import ftplib
import pathlib
import shutil
import string
from typing import Any, Dict, List, Optional

from app_components.ongoing_recommendation import get_recommendation_process_components
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
from gluon.contrib.appconfig import AppConfig # type: ignore
from gluon import current

import zipfile as z


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
        recommendation_process: Any = get_recommendation_process_components(self._article)
        process = recommendation_process['components']
        
        latex_code: List[str] = []
        first_round = True

        for round in process:
            if not round:
                continue

            latex_round: List[str] = []

            round_number: int = round['roundNumber']
            latex_round.append(f"\\subsection*{{Evaluation round #{round_number}}}")

            recommendation_manuscrit = self._html_to_latex.convert(self._str(round['manuscriptDoi']))
            if recommendation_manuscrit:
                recommendation_manuscrit = recommendation_manuscrit.lstrip("Manuscript:").strip()
                if recommendation_manuscrit:
                    latex_round.append(f"\nDOI or URL of the preprint: {recommendation_manuscrit}")

            recommendation_version = self._html_to_latex.convert(self._str(round['recommendationVersion']))
            if recommendation_version:
                recommendation_version = recommendation_version.lstrip('version:').strip()
                if recommendation_version:
                    latex_round.append(f"\nVersion of the preprint: {recommendation_version}")

            latex_round.extend(self._get_round_author_reply(round))
            latex_round.extend(self._get_round_recommender_decision(round, first_round))
            latex_round.extend(self._get_round_reviews(round))
            
            if len(latex_round) > 1:
                latex_code.extend(latex_round)
            
            first_round = False
                
        return template.replace(f"[[{var_title.upper()}]]", "\n".join(latex_code))
    

    def _get_round_reviews(self, round: Dict[str, Any]):
        latex_lines: List[str] = []
        reviews: List[Dict[str, Any]] = round['reviewsList']
                
        for review in reviews:
            review_author = self._html_to_latex.convert(self._str(review['authors']))
            if not review_author:
                continue

            review_content = self._html_to_latex.convert(self._str(review['text']))
            if review_content:
                latex_lines.append(f"\\subsubsection*{{Reviewed by {review_author}}}")
                latex_lines.append(review_content)

            review_link = self._html_to_latex.convert(self._str(review['pdfLink']))
            if review_link:
                latex_lines.append(f"\n{review_link}")
        return latex_lines


    def _get_round_recommender_decision(self, round: Dict[str, Any], first_round: bool):
        latex_lines: List[str] = []

        recommender_decision = self._str(round['recommendationText'])
        if recommender_decision:
            recommender_decision = self._remove_references_in_recommendation_decision(recommender_decision)
        recommender_decision = self._html_to_latex.convert(recommender_decision)

        if recommender_decision and not first_round:
            
            recommendation_label = f"Decision"

            recommendation_author = self._html_to_latex.convert(self._str(round['recommendationAuthorName']))
            if recommendation_author:
                recommendation_label += f" by {recommendation_author}"

            recommendation_post_date = self._html_to_latex.convert(self._str(round['recommendationDate']))
            if recommendation_post_date:
                recommendation_label += f", posted {recommendation_post_date}"

            recommendation_validation_date = self._html_to_latex.convert(self._str(round['recommendationValidationDate']))
            if recommendation_validation_date:
                recommendation_validation_date += f", validated {recommendation_validation_date}"

            recommendation_status = self._html_to_latex.convert(self._str(round['recommendationStatus']))
            if recommendation_status:
                recommendation_label += f": {recommendation_status}"
            latex_lines.append(f"\\subsubsection*{{{recommendation_label}}}")

            recommendation_title = self._html_to_latex.convert(self._str(round['recommendationTitle']))
            if recommendation_title:
                latex_lines.append(f"\\subsubsubsection{{{recommendation_title}}}")
                latex_lines.append(r"\smallbreak")
            latex_lines.append(recommender_decision)
        return latex_lines


    def _get_round_author_reply(self, round: Dict[str, Any]):
        latex_lines: List[str] = []
        author_reply = self._html_to_latex.convert(self._str(round['authorsReply']))
        author_reply_date = self._str(round['authorsReplyDate'])
        if author_reply:
            author_reply_title = "Authors' reply"
            if author_reply_date:
                author_reply_title += f", {author_reply_date}"
            latex_lines.append(f"\\subsubsection*{{{author_reply_title}}}")
            latex_lines.append(f"{author_reply}")

        author_reply_pdf_link = self._html_to_latex.convert(self._str(round['authorsReplyPdfLink']))
        if author_reply_pdf_link:
            latex_lines.append(f"\n{author_reply_pdf_link}")

        author_reply_track_change_file = self._html_to_latex.convert(self._str(round['authorsReplyTrackChangeFileLink']))
        if author_reply_track_change_file:
            latex_lines.append(f"\n{author_reply_track_change_file}")
        
        return latex_lines


    def _str(self, value: ...):
        if value is None:
            return ''
        else:
            return str(value)


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
            user, passwd = (self.CLOCKSS_USERNAME, self.CLOCKSS_PASSWORD)
            client = ftplib.FTP()
            client.connect(host, int(port))
            client.login(user, passwd)
            return client
        else:
            raise NoOptionError('server/username/password', 'clockss')


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
