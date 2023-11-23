from typing import cast, List
from pydal.objects import Row
from pydal import DAL


class Membership(Row):
    id: int
    user_id: int
    group_id: int


    @staticmethod
    def get_all(db: DAL):
        return cast(List[Membership], db(db.auth_membership).select())
    

    @staticmethod
    def get_by_user_id(db: DAL, user_id: int):
        return cast(List[Membership], db(db.auth_membership.user_id == user_id).select())
    

    @staticmethod
    def has_membership(db: DAL, user_id: int):
        membership = Membership.get_by_user_id(db, user_id)
        return len(membership) > 0
