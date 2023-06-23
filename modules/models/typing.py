from typing import Union, cast

def _(typ):
    return Union[typ, None]

def _cast(typ, val):
    return cast(_(typ), val)
