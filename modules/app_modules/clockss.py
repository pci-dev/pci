from dataclasses import dataclass
import datetime
import os
import ftplib
import pathlib
import re
import shutil
import string
from typing import Any, Dict, List, Optional, Union, cast

from app_components.ongoing_recommendation import get_recommendation_process_components
from app_modules.html_to_latex import HtmlToLatex
from app_modules.common_small_html import build_citation, mkSimpleDOI, mkUser
from configparser import NoOptionError
from models.article import Article
from models.pdf import PDF
from models.press_reviews import PressReview
from models.review import Review, ReviewState
from models.recommendation import Recommendation
from app_modules import crossref
from app_modules import common_tools

from gluon.html import A, SPAN, TAG
from gluon.contrib.appconfig import AppConfig # type: ignore
from gluon import current

import zipfile as z


myconf = AppConfig(reload=True)
pci_RR_activated = bool(myconf.get("config.registered_reports", default=False))

@dataclass
class TemplateVar():
    value: Optional[Any]
    is_latex_code: bool
    avoid_missing_value: bool

    def __init__(self, value: ..., is_latex_code: bool = False, avoid_missing_value: bool = False):
        self.value = value
        self.is_latex_code = is_latex_code
        self.avoid_missing_value = avoid_missing_value


class Clockss:

    CLOCKSS_SERVER: Optional[str] = myconf.get("clockss.server")
    CLOCKSS_USERNAME: Optional[str] = myconf.get("clockss.username")
    CLOCKSS_PASSWORD: Optional[str] = myconf.get("clockss.password")

    LATEX_TEMPLATE_FILENAME = 'main.tex'
    PDFLATEX_BIN: Optional[str] = myconf.get("latex.pdflatex")

    DATE_FORMAT = "%d %B %Y"
    
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
        crossref.init_conf()
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

        template_vars: Dict[str, Any] = {
            'ARTICLE_AUTHORS': TemplateVar(self._article.authors),
            'ARTICLE_TITLE': TemplateVar(self._get_formatted_article_title(), True),
            'RECOMMENDATION_ABSTRACT': TemplateVar(self._remove_references_in_recommendation_decision(self._recommendation.recommendation_comments or '')),
            'ARTICLE_YEAR': TemplateVar(self._article.article_year),
            'ARTICLE_VERSION': TemplateVar(self._article.ms_version),
            'ARTICLE_COVER_LETTER': TemplateVar(self._article.cover_letter),
            'RECOMMENDATION_TITLE': TemplateVar(self._get_recommendation_title(), True),
            'RECOMMENDATION_DOI': TemplateVar(mkSimpleDOI(self._recommendation.doi)),
            'PREPRINT_SERVER': TemplateVar(self._article.preprint_server),
            'RECOMMENDATION_CITATION': TemplateVar(build_citation(self._article, self._recommendation, True)),
            'RECOMMENDATION_VALIDATION_DATE': TemplateVar(self._recommendation.validation_timestamp.strftime(self.DATE_FORMAT) if self._recommendation.validation_timestamp else None),
            'PCI_NAME': TemplateVar(self._str(myconf.take("app.description"))),
            'ARTICLE_VALIDATION_DATE': TemplateVar(self._get_article_validation_date()),
            'RECOMMENDATION_REFERENCES': TemplateVar(self._get_list_references_in_template(), True, True),
            'RECOMMENDATION_PROCESS': TemplateVar(self._replace_recommendation_process(), True),
            'PCI_IMG': TemplateVar(self._replace_img_in_template(), True),
            'RECOMMENDATION_SUBTITLE': TemplateVar(self._get_recommendation_subtitle(), True)
        }

        for variable_name, variable_value in template_vars.items():
            template = self._replace_var_in_template(variable_name, variable_value, template)

        return template
    

    def _get_recommendation_subtitle(self):
        recommenders_name = self._get_recommender_name()
        reviewers_name = self._get_reviewers_names()

        subtitle = f"{recommenders_name} based on peer reviews by {reviewers_name}"
        if pci_RR_activated and self._article.report_stage:
            subtitle = f"A recommendation by {subtitle} of the {self._article.report_stage} REPORT:"
        return subtitle

    def _get_recommendation_title(self):
        title = self._recommendation.recommendation_title
        if not title:
            return
        
        title = title.strip()
        title = self._html_to_latex.convert_LaTeX_special_chars(title)
        title = self._convert_stars_to_italic(title)
        return title


    def _get_article_validation_date(self):
        validation_date: Optional[datetime.datetime] = None

        if self._article.validation_timestamp:
            validation_date = self._article.validation_timestamp
        elif self._article.upload_timestamp:
            validation_date = self._article.upload_timestamp

        if validation_date:
            return validation_date.strftime(self.DATE_FORMAT)


    def _get_formatted_article_title(self):
        title = self._article.title
        if not title:
            return
        
        title = title.strip()
        title = self._html_to_latex.convert_LaTeX_special_chars(title)
        title = self._convert_stars_to_italic(title)
        
        has_punctuation = bool(re.search(r"[?!…¿;¡.]$", title))
        if has_punctuation:
            return title
        else:
            return f"{title}."
    

    def _convert_stars_to_italic(self, text: str):
        text = re.sub(r'\*(.*?)\*', r'\\textit{\1}', text)
        return text


    def _get_reviewers_names(self):
        reviews = Review.get_by_article_id_and_state(self._article.id, ReviewState.REVIEW_COMPLETED)
        nb_anonymous = 0
        names: List[str] = []
        user_id: List[int] = []
        for review in reviews:
            if not review.anonymously and review.reviewer_id not in user_id:
                reviewer_html: Union[A, SPAN] = mkUser(current.auth, current.db, review.reviewer_id, linked=True, orcid=True)
                reviewer_name = self._html_to_latex.convert(self._str(reviewer_html))
                if isinstance(reviewer_html, SPAN) and len(reviewer_html.components) == 2: # type: ignore
                    reviewer_name = self._html_to_latex.convert(self._str(reviewer_html.components[0])) # type: ignore
                    reviewer_orcid = str(reviewer_html.components[1].attributes['_href']) # type: ignore
                    reviewer_name += f"\\href{{{reviewer_orcid}}}{{\\hspace{{2px}}\\includegraphics[width=10px,height=10px]{{ORCID_ID.png}}}}"
                
                names.append(reviewer_name)
                if review.reviewer_id:
                    user_id.append(review.reviewer_id)
        
        user_id.clear()

        for review in reviews:
            if review.anonymously and review.reviewer_id not in user_id:
                nb_anonymous += 1
                if review.reviewer_id:
                    user_id.append(review.reviewer_id)
        
        if (nb_anonymous > 0):
            anonymous = str(nb_anonymous) + ' anonymous reviewer'
            if (nb_anonymous > 1):
                anonymous += 's'
            names.append(anonymous)
        
        formatted_names = ''
        for i, name in enumerate(names):
            if i == 0:
                formatted_names = name
            elif i == len(names) - 1:
                formatted_names += f' and {name}'
            else:
                formatted_names += f', {name}'

        return formatted_names


    def _get_recommender_name(self):
        db = current.db

        recommendations = cast(List[Recommendation], db(db.t_recommendations.id == self._recommendation.id)\
            .select(db.t_recommendations.ALL, distinct=db.t_recommendations.recommender_id))
        press_reviews = cast(List[PressReview], db((db.t_recommendations.id == self._recommendation.id) & (db.t_press_reviews.recommendation_id == db.t_recommendations.id))\
            .select(db.t_press_reviews.ALL, distinct=db.t_press_reviews.contributor_id))
        
        recommenders_id: List[int] = []
        for recommendation in recommendations:
            recommenders_id.append(recommendation.recommender_id)

        for press_review in press_reviews:
            if press_review.contributor_id:
                recommenders_id.append(press_review.contributor_id)

        recommender_names: List[str] = []
        for recommender_id in recommenders_id:
            recommender_html: Union[A, SPAN] = mkUser(current.auth, current.db, recommender_id, linked=True, orcid=True)
            recommender_name = self._html_to_latex.convert(self._str(recommender_html))
            if isinstance(recommender_html, SPAN) and len(recommender_html.components) == 2: # type: ignore
                recommender_name = self._html_to_latex.convert(self._str(recommender_html.components[0])) # type: ignore
                recommender_orcid = str(recommender_html.components[1].attributes['_href']) # type: ignore
                recommender_name += f"\\href{{{recommender_orcid}}}{{\\hspace{{2px}}\\includegraphics[width=10px,height=10px]{{ORCID_ID.png}}}}"
            recommender_names.append(recommender_name)

        if len(recommender_names) == 1:
            return recommender_names[0]
        else:
            return ' and '.join([', '.join(recommender_names[:-1]), recommender_names[-1]])


    def _replace_img_in_template(self):
        pci = str(myconf.take("app.description")).lower()
        img_map = {
            'peer community in registered reports (test)': 'logo_PDF_rr.jpg',
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
            'peer community in health and movement sciences': 'logo_PDF_healthandmovementsciences.jpg',
            'peer community in microbiology': 'logo_PDF_microbiology.jpg',
            'peer community in organization studies': 'logo_PDF_organizationstudies.jpg',
            'peer community in computational statistics': 'logo_PDF_computationalstatistics.jpg',
            'peer community in psychology': 'logo_PDF_psychology.jpg',
        }
        img = img_map.get(pci, 'logo_PDF_evolbiol.jpg')
        return img
    

    def _replace_recommendation_process(self):
        recommendation_process: Any = get_recommendation_process_components(self._article)
        process = recommendation_process['components']
        
        latex_code: List[str] = []
        first_round = True

        for round in process:
            if not round:
                continue

            latex_round: List[str] = []

            round_number: int = round['roundNumber']
            latex_round.append(f"\\section*{{Evaluation round \\#{round_number}}}")

            if not first_round:
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
            if not first_round:
                latex_round.extend(self._get_round_recommender_decision(round))
            latex_round.extend(self._get_round_reviews(round))
            
            if len(latex_round) > 1:
                latex_code.extend(latex_round)

            if first_round:
                first_round = False

        return "\n".join(latex_code)
    

    def _get_round_reviews(self, round: Dict[str, Any]):
        latex_lines: List[str] = []
        reviews: List[Dict[str, Any]] = round['reviewsList']
                
        for review in reviews:
            reviewer_name = self._html_to_latex.convert(self._str(review['authors']))
            if not reviewer_name:
                continue

            review_instance = cast(Review, review['review'])
            if review_instance:
                review_date: datetime.datetime = review['reviewDatetime']
                review_date_str = review_date.strftime(self.DATE_FORMAT)
                reviewer_name = reviewer_name.rsplit(', ', 1)[0]

                if not review_instance.anonymously:
                    html_reviewer = mkUser(current.auth, current.db, review_instance.reviewer_id, True, orcid=True)
                    reviewer: Optional[Union[A, SPAN]] = html_reviewer
                    reviewer_orcid: Optional[str] = None
                    if isinstance(html_reviewer, SPAN) and len(html_reviewer.components) == 2: #type: ignore
                        reviewer = cast(A, html_reviewer.components[0]) # type: ignore
                        reviewer_orcid = str(html_reviewer.components[1].attributes['_href']) # type: ignore

                    if isinstance(reviewer, A):
                        reviewer_link = str(reviewer.attributes['_href']) # type: ignore
                        reviewer_name = f"\\href{{{reviewer_link}}}{{{reviewer_name}}}"
                        if reviewer_orcid:
                            reviewer_name += f"\\href{{{reviewer_orcid}}}{{\\hspace{{2px}}\\includegraphics[width=9px,height=9px]{{ORCID_ID.png}}}}"
                
                reviewer_name += f", {review_date_str}"

            review_content = self._html_to_latex.convert(self._str(review['text']))
            if review_content:
                latex_lines.append(f"\\subsection*{{Reviewed by {reviewer_name}}}")
                latex_lines.append(review_content)

            review_link = self._html_to_latex.convert(self._str(review['pdfLink']))
            if review_link:
                latex_lines.append(f"\n{review_link}")

        return latex_lines


    def _get_round_recommender_decision(self, round: Dict[str, Any]):
        latex_lines: List[str] = []

        recommendation_pdf_link = self._html_to_latex.convert(self._str(round['recommendationPdfLink']))
        recommender_decision = self._str(round['recommendationText'])
        if recommender_decision:
            recommender_decision = self._remove_references_in_recommendation_decision(recommender_decision)
        recommender_decision = self._html_to_latex.convert(recommender_decision)

        if recommender_decision or recommendation_pdf_link:
            
            recommendation_label = f"Decision"

            recommendation_author = self._html_to_latex.convert(self._str(round['recommendationAuthorName']))
            if recommendation_author:
                recommendation_label += f" by {recommendation_author}"

            recommender_id = int(round['recommenderId'])
            recommender = mkUser(current.auth, current.db, recommender_id, linked=False, orcid=True)
            if isinstance(recommender, SPAN) and len(recommender.components) == 2: # type: ignore
                recommender_orcid = str(recommender.components[1].attributes['_href']) # type: ignore
                recommendation_label += f"\\href{{{recommender_orcid}}}{{\\hspace{{2px}}\\includegraphics[width=9px,height=9px]{{ORCID_ID.png}}}}"

            recommendation_post_date: Optional[datetime.datetime] = round['recommendationDatetime']
            if recommendation_post_date:
                recommendation_post_date_str = recommendation_post_date.strftime(self.DATE_FORMAT)
                recommendation_label += f", posted {recommendation_post_date_str}"

            recommendation_validation_date: Optional[datetime.datetime] = round['recommendationValidationDatetime']
            if recommendation_validation_date:
                recommendation_validation_date_str = recommendation_validation_date.strftime(self.DATE_FORMAT)
                recommendation_label += f", validated {recommendation_validation_date_str}"

            latex_lines.append(f"\\subsection*{{{recommendation_label}}}")

            recommendation_title = self._html_to_latex.convert(self._str(round['recommendationTitle']))

            if recommendation_title:
                latex_lines.append(recommendation_title)
                latex_lines.append(r"\smallbreak")

            if recommender_decision:
                latex_lines.append(recommender_decision)

            if recommendation_pdf_link:
                latex_lines.append(recommendation_pdf_link)
                
        return latex_lines


    def _get_round_author_reply(self, round: Dict[str, Any]):
        latex_lines: List[str] = []
        author_reply = self._html_to_latex.convert(self._str(round['authorsReply']))
        author_reply_date: Optional[datetime.datetime] = round['authorsReplyDatetime']
        author_reply_pdf_link = self._html_to_latex.convert(self._str(round['authorsReplyPdfLink']))
        author_reply_track_change_file = self._html_to_latex.convert(self._str(round['authorsReplyTrackChangeFileLink']))

        if author_reply or author_reply_pdf_link or author_reply_track_change_file:
            author_reply_title = "Authors' reply"
            if author_reply_date:
                author_reply_date_str = author_reply_date.strftime(self.DATE_FORMAT)
                author_reply_title += f", {author_reply_date_str}"
            latex_lines.append(f"\\subsection*{{{author_reply_title}}}")
        
        if author_reply:
            latex_lines.append(f"{author_reply}")

        if author_reply_pdf_link:
            latex_lines.append(f"\n{author_reply_pdf_link}")
        
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
        reference_start = False

        for line in lines:
            sub_lines = line.split('<br>&nbsp;<br>')
            for sub_line in sub_lines:
                try:
                    line_text = str(TAG(sub_line).flatten().lower().strip()) # type: ignore
                except:
                    line_text = sub_line
                line_text = line_text.translate(str.maketrans('', '', string.punctuation))

                if line_text in ['reference', 'references']:
                    reference_start = True
                    break

                recommendation_text.append(f"\n{sub_line}")
            
            if reference_start:
                break

        return '\n'.join(recommendation_text)
    

    def _replace_var_in_template(self, var_title: str, template_var: TemplateVar, template: str):
        content = self._str(template_var.value)
        
        if content:
            if not template_var.is_latex_code:
                content = self._html_to_latex.convert(content)
            content = self._replace_url_in_content(content)
        else:
            if not template_var.avoid_missing_value:
                content = f"Missing {var_title.lower()}"
            content = self._html_to_latex.convert_LaTeX_special_chars(content)

        return template.replace(f"[[{var_title.upper()}]]", content)
    

    def _replace_url_in_content(self, latex_content: str):
        regex = r"(?<!\{)(https?://?[\w-]+\.[^;:<>{}\[\]\"\'\s~]*[^.,;?!:<>{}\[\]()\"\'\s~\\])(?!\})"
        pattern = re.compile(regex)
        match = pattern.search(latex_content)

        if match:
            replacement = r"\\url{\1}"
            latex_content = re.sub(regex, replacement, latex_content)
        
        return latex_content
    

    def _get_list_references_in_template(self):
        references: List[str] = Recommendation.get_references(self._recommendation)

        if len(references) == 0:
            return
        
        content: List[str] = [r'\textbf{\emph{References: }}',
                              r'\begin{flushleft}',
                              r'\begin{itemize}']
        for reference in references:
            reference = self._html_to_latex.convert(reference)
            content.append(f"\\item[]{{}} {reference}")
        content.append(r'\end{itemize}')
        content.append(r'\end{flushleft}')
        return '\n'.join(content)


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
