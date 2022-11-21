from PIL import Image
from io import BytesIO


def resizeImage(data, size, format="PNG"):
    im = Image.open(BytesIO(data))
    im.thumbnail(size, Image.ANTIALIAS)
    ba = BytesIO()
    im.save(ba, format=format)
    return ba.getvalue()


# from gluon.contrib.imageutils import RESIZE

class RESIZE:

    def __init__(self, x, y, format='PNG'):
        self.size = (x, y)
        self.format = format

    def __call__(self, value):
        if not hasattr(value, 'value'):
            return (value, None)

        try:
            data = resizeImage(value.value, self.size, self.format)
            value.file = BytesIO(data)
        except Exception as e:
            return (value, "resize error: " + str(e))
        else:
            return (value, None)
