from typing import Optional
from gluon.dal import SQLCustomType

class OrcidTools:
    @staticmethod
    def add_hyphen(value: Optional[str]):
        if not value or len(value) == 0:
            return None
        return '-'.join(value[i:i+4] for i in range(0, len(value), 4))

    @staticmethod
    def remove_hyphen(value: Optional[str]):
        if not value or len(value) == 0:
            return None
        return value.replace('-', '')


ORCID_NUMBER_FIELD_TYPE = SQLCustomType("string", "string", OrcidTools.remove_hyphen, OrcidTools.add_hyphen)

class OrcidValidator:
    def __init__(self):
        self.error_message = 'Invalid ORCID number'

    def __call__(self, value: Optional[str]):
        value = OrcidTools.remove_hyphen(value)
        if not value or len(value) == 0:
            return value, None

        if len(value) != 16:
            return value, f'{self.error_message}: expected length 16, got {len(value)}'
        
        if not value.isdigit():
            return value, f'{self.error_message}: must contain only digits'
        
        return value, None
