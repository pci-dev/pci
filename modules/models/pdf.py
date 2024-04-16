import os
from typing import Optional as _
from typing import TYPE_CHECKING

from pydal.objects import Row
from gluon import current

if TYPE_CHECKING:
    from models.recommendation import Recommendation

class PDF(Row):
    id: int
    recommendation_id: int
    pdf: str
    pdf_data: bytes


    @staticmethod
    def get_by_id(id: int) -> _['PDF']:
        db = current.db
        return db.t_pdf[id]
    

    @staticmethod
    def get_by_recommendation_id(recommendation_id: int):
        db = current.db
        pdf: _[PDF] = db(db.t_pdf.recommendation_id == recommendation_id).select().first()
        return pdf

    @staticmethod
    def save_pdf_to_db(recommendation: 'Recommendation', directory: str, filename: str, overwrite: bool = True):        
        if overwrite:
            PDF.delete_pdf_to_db(recommendation.id)

        pdf_id = int(current.db.t_pdf.insert(recommendation_id=recommendation.id, pdf=filename))
        pdf = PDF.get_by_id(pdf_id)

        if pdf:
            file_to_upload = os.path.join(directory, filename)
            data = open(file_to_upload, 'rb')
            data = data.read()
            filename = current.db.t_pdf.pdf.store(data, filename)
            pdf.update_record(pdf=filename, pdf_data=data)


    @staticmethod
    def delete_pdf_to_db(recommendation_id: int):
        pdf = PDF.get_by_recommendation_id(recommendation_id)
        if pdf:
            pdf.delete_record()
