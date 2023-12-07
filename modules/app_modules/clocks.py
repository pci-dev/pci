import os, pathlib
from app_modules import crossref
import zipfile as z

def build_xml(db, request, art):
    attachments_dir, base_dir = init_dir(db, request, art.id)
    red = db.get_last_recomm(art)
    filename = f"{attachments_dir}/{base_dir}.xml"
    xodo = crossref.crossref_xml(red)
    with open(filename, 'wb') as file:
        file.write(xodo.encode('utf8'))
    zip_directory(attachments_dir)

def init_dir(db, request, article_id):
    host = db.cfg.host
    base_dir = f'pci.{host}.100{article_id}'
    attachments_dir = os.path.join(request.folder, "clocks", base_dir)
    os.makedirs(attachments_dir, exist_ok=True)

    return attachments_dir, base_dir

def build_pdf(db, art):
    pass


def zip_directory(filepath):
    direc = pathlib.Path(filepath)
    with z.ZipFile(f'{filepath}.zip', 'w', z.ZIP_DEFLATED) as zp:
        for file_path in direc.iterdir():
            zp.write(file_path, arcname=file_path.name)
