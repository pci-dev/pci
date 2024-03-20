import os
import ftplib
import pathlib
import shutil
from models.article import Article
import zipfile as z
from models.recommendation import Recommendation
from app_modules import crossref
from app_modules import common_tools
from gluon.contrib.appconfig import AppConfig
from gluon import current


myconf = AppConfig(reload=True)


class ClockssUpload:

    CLOCKSS_SERVER = str(myconf.take("clockss.server"))
    CLOCKSS_USERNAME = str(myconf.take("clockss.username"))
    CLOCKSS_PASSWORD = str(myconf.take("clockss.password"))
    CLOCKSS_FTP_SESSION = ftplib.FTP(CLOCKSS_SERVER, CLOCKSS_USERNAME, CLOCKSS_PASSWORD) 

    LATEX_TEMPLATE_FILENAME = 'clockss.tex'
    PDFLATEX_BIN = str(myconf.take("latex.pdflatex"))
    
    _article: Article
    _prefix: str
    _recommendation: Recommendation

    attachments_dir: str

    def __init__(self, article: Article):
        self._article = article
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
        os.makedirs(tmp_folder)

        latex_file_path = f"{tmp_folder}/{self._prefix}.tex"
        print(latex_content, file=open(latex_file_path, 'w'))

        os.system(f'{self.PDFLATEX_BIN} --output-directory={tmp_folder} {latex_file_path}')
        shutil.move(f"{tmp_folder}/{self._prefix}.pdf", pdf_dest_path)
        shutil.rmtree(tmp_folder)


    def _build_latex_content_from_template(self):
        template = self._get_latex_template_content()
        if not self._recommendation.recommendation_title:
            return
        template = template.replace('[[TEXT]]', self._recommendation.recommendation_title)
        return template


    def _get_latex_template_content(self):
        template_path = f"{current.request.folder}/templates/{self.LATEX_TEMPLATE_FILENAME}"
        with open(template_path, 'r') as template:
            return template.read()


    def _zip_directory(self, filepath: str):
        direc = pathlib.Path(filepath)
        with z.ZipFile(f'{filepath}.zip', 'w', z.ZIP_DEFLATED) as zp:
            for file in direc.iterdir():
                zp.write(file, arcname=file.name)


    def compile_and_send(self):
        self._build_xml()
        self._zip_directory(self.attachments_dir)
        filename = self.attachments_dir + ".zip"
        with open(filename, 'rb') as file:
            self.CLOCKSS_FTP_SESSION.storbinary(f'STOR {self._prefix}.zip', file)
        #delete files after upload
        shutil.rmtree(self.attachments_dir)
        os.remove(filename)
        self.CLOCKSS_FTP_SESSION.quit()
