from typing import cast, List
from models.group import Role
from pydal.objects import Row
from gluon import current


class Membership(Row):
    id: int
    user_id: int
    group_id: int

    
    @staticmethod
    def get_all(roles: List[Role] = []):
        db = current.db
        if len(roles) == 0:
            return cast(List[Membership], db(db.auth_membership).select())
        
        role_values: List[str] = []
        for role in roles:
            role_values.append(role.value)

        memberships = db((db.auth_membership.group_id == db.auth_group.id) & (db.auth_group.role.belongs(role_values))).select(db.auth_membership.ALL)
        return cast(List[Membership], memberships)
    

    @staticmethod
    def get_by_user_id(user_id: int, roles: List[Role] = []):
        db = current.db
        if len(roles) == 0:
            return cast(List[Membership], db(db.auth_membership.user_id == user_id).select())

        role_values: List[str] = []
        for role in roles:
            role_values.append(role.value)

        memberships = db((db.auth_membership.group_id == db.auth_group.id) & (db.auth_group.role.belongs(role_values)) & (db.auth_membership.user_id == user_id)).select(db.auth_membership.ALL)
        return cast(List[Membership], memberships)
    

    @staticmethod
    def has_membership(user_id: int, roles: List[Role] = []):
        membership = Membership.get_by_user_id(user_id, roles)
        return len(membership) > 0
    
    @staticmethod
    def remove_all_membership(user_id: int) -> int:
        db = current.db
        return db(db.auth_membership.user_id == user_id).delete()
