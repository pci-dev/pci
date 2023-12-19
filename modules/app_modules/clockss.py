import os, pathlib
from app_modules import crossref
import pdfkit
from gluon.html import *
import zipfile as z
from gluon.contrib.appconfig import AppConfig
from app_modules import common_tools

myconf = AppConfig(reload=True)
scheme = myconf.take("alerts.scheme")
host = myconf.take("alerts.host")
port = myconf.take("alerts.port", cast=lambda v: common_tools.takePort(v))

class CLOCKSS_UPLOAD:
    def __init__(self, db, request, article):
        self.db = db
        self.request = request
        self.article = article

    def build_xml(self):
        attachments_dir, base_dir = self.init_dir()
        red = self.db.get_last_recomm(self.article)
        filename = f"{attachments_dir}/{base_dir}.xml"
        xodo = crossref.crossref_xml(red)
        with open(filename, 'wb') as file:
            file.write(xodo.encode('utf8'))


    def init_dir(self):
        base_dir = common_tools.generate_recommendation_doi(self.article.id)[9:]
        attachments_dir = os.path.join(self.request.folder, "clockss", base_dir)
        os.makedirs(attachments_dir, exist_ok=True)
        return attachments_dir, base_dir

    def build_pdf(self):
        options = {
            'cookie' : self.request.cookies.items()
        }
        attachments_dir, base_dir = self.init_dir()
        filename = f"{attachments_dir}/{base_dir}.pdf"
        printable_page = URL(c="articles", f= "rec", vars=dict(articleId=self.article.id, printable=True), host=host, scheme=scheme, port=port)
        pdfkit.from_url(printable_page, filename, options=options)
        return f"{base_dir}.pdf"
        
    def zip_directory(self, filepath):
        direc = pathlib.Path(filepath)
        with z.ZipFile(f'{filepath}.zip', 'w', z.ZIP_DEFLATED) as zp:
            for file_path in direc.iterdir():
                zp.write(file_path, arcname=file_path.name)

