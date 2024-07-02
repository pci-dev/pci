from typing import List, Optional, Union

from gluon.html import DIV, SPAN
from pydal.objects import Field
from pydal.validators import IS_IN_SET, IS_NOT_EMPTY, Validator, IS_LIST_OF


class RequiredField(Field):
    def __init__(self, *args: ..., **kwargs: ...):
        requires: Optional[Union[List[Validator], Validator]] = kwargs.get('requires')
        if not requires:
            kwargs.setdefault('requires', IS_NOT_EMPTY())
        else:
            if not isinstance(requires, List):
                requires = [requires]

            is_not_empty = False
            for v in requires:
                if type(v) in [IS_NOT_EMPTY, IS_IN_SET, IS_LIST_OF]:
                    is_not_empty = True
            if not is_not_empty:
                requires.append(IS_NOT_EMPTY())

            if len(requires) == 1:
                kwargs['requires'] = requires[0]
            else:
                kwargs['requires'] = requires


        label: Optional[Union[DIV, str]] = kwargs.get('label')
        if label:
            label = SPAN(label, SPAN(" * ", _style="color:red;"))
        kwargs['label'] = label
        
        super().__init__(*args, **kwargs) # type: ignore
