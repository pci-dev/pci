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
    def save_pdf_to_db(recommendation: 'Recommendation', directory: str, filename: str):
        pdf_id = int(current.db.t_pdf.insert(recommendation_id=recommendation.id, pdf=filename))
        pdf = PDF.get_by_id(pdf_id)
        file_to_upload = os.path.join(directory, filename)
        data = open(file_to_upload, 'rb')
        data = data.read()
        filename = current.db.t_pdf.pdf.store(data, filename)
        pdf.update_record(pdf=filename, pdf_data=data)
