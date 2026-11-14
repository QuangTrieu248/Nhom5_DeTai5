from flask_login import UserMixin
from sqlalchemy import Column, Integer, String, Enum
from eapp import db
from enum import Enum as UserEnum


class BaseModel(db.Model):
    __abstract__ = True

    id = Column(Integer, primary_key=True, autoincrement=True)


class UserRoleEnum(UserEnum):
    ADMIN = 1
    USER = 2
    STAFF = 3


class User(BaseModel, UserMixin):
    name = Column(String(50), nullable=False)
    avatar = Column(String(100), nullable=True)
    username = Column(String(50), nullable=False, unique=True)
    password = Column(String(100), nullable=False)
    user_role = Column(Enum(UserRoleEnum), default=UserRoleEnum.USER)

    def __str__(self):
        return self.name