import os
import ftplib
import pathlib
import shutil
import pdfkit
import zipfile as z
from gluon.html import *
from app_modules import crossref
from app_modules import common_tools
from gluon.contrib.appconfig import AppConfig

myconf = AppConfig(reload=True)
scheme = myconf.take("alerts.scheme")
host = myconf.take("alerts.host")
port = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))
server = myconf.take("clockss.server")
username = myconf.take("clockss.username")
password = myconf.take("clockss.password")
session = ftplib.FTP(server, username, password) 

class CLOCKSS_UPLOAD:
    def __init__(self, db, request, article):
        self.db = db
        self.request = request
        self.article = article
        self.attachments_dir, self.prefix = self.init_dir()

    def build_xml(self):
        recomm = self.db.get_last_recomm(self.article)
        filename = f"{self.attachments_dir}/{self.prefix}.xml"
        crossref.init_conf(self.db)
        recomm_xml = crossref.crossref_xml(recomm)
        with open(filename, 'wb') as file:
            file.write(recomm_xml.encode('utf8'))


    def init_dir(self):
        prefix = common_tools.generate_recommendation_doi(self.article.id)[9:]
        attachments_dir = os.path.join(self.request.folder, "clockss", prefix)
        os.makedirs(attachments_dir, exist_ok=True)
        return attachments_dir, prefix

    def build_pdf(self):
        options = {
            'cookie' : self.request.cookies.items()
        }
        filename = f"{self.attachments_dir}/{self.prefix}.pdf"
        printable_page = URL(c="articles", f= "rec", vars=dict(articleId=self.article.id, printable=True), host=host, scheme=scheme, port=port)
        pdfkit.from_url(printable_page, filename, options=options)
        return f"{self.prefix}.pdf"
        
    def zip_directory(self, filepath):
        direc = pathlib.Path(filepath)
        with z.ZipFile(f'{filepath}.zip', 'w', z.ZIP_DEFLATED) as zp:
            for file in direc.iterdir():
                zp.write(file, arcname=file.name)

    def compile_and_send(self):
        self.build_xml()
        self.zip_directory(self.attachments_dir)
        filename = self.attachments_dir + ".zip"
        with open(filename, 'rb') as file:
            session.storbinary(f'STOR {self.prefix}.zip', file)
        #delete files after upload
        shutil.rmtree(self.attachments_dir), os.remove(filename)
        session.quit()
