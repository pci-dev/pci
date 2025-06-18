from typing import cast, List
from .group import Role
from pydal.objects import Row
from ...common import db, auth

class Membership(Row):
    id: int
    user_id: int
    group_id: int


    @staticmethod
    def get_all(roles: List[Role] = []):
        if len(roles) == 0:
            return cast(List[Membership], db(db.auth_membership).select())

        role_values: List[str] = []
        for role in roles:
            role_values.append(role.value)

        memberships = db((db.auth_membership.group_id == db.auth_group.id) & (db.auth_group.role.belongs(role_values))).select(db.auth_membership.ALL)
        return cast(List[Membership], memberships)


    @staticmethod
    def get_by_user_id(user_id: int, roles: List[Role] = []):
        if len(roles) == 0:
            return cast(List[Membership], db(db.auth_membership.user_id == user_id).select())

        role_values: List[str] = []
        for role in roles:
            role_values.append(role.value)

        memberships = db((db.auth_membership.group_id == db.auth_group.id) & (db.auth_group.role.belongs(role_values)) & (db.auth_membership.user_id == user_id)).select(db.auth_membership.ALL)
        return cast(List[Membership], memberships)


    @staticmethod
    def has_membership(user_id: int = auth.user_id, role: List[Role] | Role = []):
        if not isinstance(role, list):
            role = [role]
        membership = Membership.get_by_user_id(user_id, role)
        return len(membership) > 0

    @staticmethod
    def remove_all_membership(user_id: int) -> int:
        return db(db.auth_membership.user_id == user_id).delete()
