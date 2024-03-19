import os
import ftplib
import pathlib
import shutil
from typing import Literal, Union
from models.article import Article
import zipfile as z
from models.recommendation import Recommendation
from app_modules import crossref
from app_modules import common_tools
from gluon.contrib.appconfig import AppConfig
from gluon import current


myconf = AppConfig(reload=True)

scheme = str(myconf.take("alerts.scheme"))
host = str(myconf.take("alerts.host"))
port: Union[int, Literal[False]] = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))
server = str(myconf.take("clockss.server"))
username = str(myconf.take("clockss.username"))
password = str(myconf.take("clockss.password"))

session = ftplib.FTP(server, username, password) 


class ClockssUpload:

    article: Article
    attachments_dir: str
    prefix: str
    recommendation: Recommendation

    def __init__(self, article: Article):
        self.article = article
        self._init_dir()
        recommendation = Article.get_last_recommendation(self.article.id)
        if not recommendation:
            raise Exception(f'No recommendation found for article with id: {self.article.id}')
        self.recommendation = recommendation


    def _build_xml(self):
        filename = f"{self.attachments_dir}/{self.prefix}.xml"
        crossref.init_conf(current.db)
        recommendation_xml = crossref.crossref_xml(self.recommendation)
        with open(filename, 'wb') as file:
            file.write(recommendation_xml.encode('utf8'))


    def _init_dir(self):
        prefix = common_tools.generate_recommendation_doi(self.article.id)[9:]
        attachments_dir = os.path.join(str(current.request.folder), "clockss", prefix)
        os.makedirs(attachments_dir, exist_ok=True)
        self.prefix = prefix
        self.attachments_dir = attachments_dir


    def build_pdf(self):
        options = {
            'cookie' : self.request.cookies.items()
        }
        filename = f"{self.attachments_dir}/{self.prefix}.pdf"
        printable_page = cast(str, URL(c="articles", f= "rec", vars=dict(articleId=self.article.id, printable=True), host=host, scheme=scheme, port=port))
        pdfkit.from_url(printable_page, filename, options=options)
        return f"{self.prefix}.pdf"
        

    def _get_latex_template(self):
        ...

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
            session.storbinary(f'STOR {self.prefix}.zip', file)
        #delete files after upload
        shutil.rmtree(self.attachments_dir)
        os.remove(filename)
        session.quit()
