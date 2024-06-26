from enum import Enum
from typing import Optional as _, cast
from pydal.objects import Row
from gluon import current


class Role(Enum):
    RECOMMENDER = 'recommender'
    MANAGER = 'manager'
    ADMINISTRATOR = 'administrator'
    DEVELOPER = 'developer'


class Group(Row):
    id: int
    role: str
    description: _[str]


    @staticmethod
    def get_by_role(role: 'Role'):
        db = current.db
        return cast(_[Group], db(db.auth_group.role == role.value).select().first())


