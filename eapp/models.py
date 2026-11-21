from flask_login import UserMixin
from sqlalchemy import Column, Integer, String, Enum, ForeignKey
from sqlalchemy.orm import relationship
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
    avatar = Column(String(100), default='/static/user_account.png')
    username = Column(String(50), nullable=False, unique=True)
    password = Column(String(100), nullable=False)
    user_role = Column(Enum(UserRoleEnum), default=UserRoleEnum.USER)
    phones = relationship('PhoneNumber', backref='user', lazy=True)

    def __str__(self):
        return self.name


class PhoneNumber(BaseModel):
    number = Column(String(20), nullable=False)
    user_id = Column(Integer, ForeignKey(User.id), nullable=False)


class Airport(BaseModel):
    name = Column(String(100), nullable=False)
    address = Column(String(255), nullable=False)

    def __str__(self):
        return self.name


class Airplane(BaseModel):
    name = Column(String(100), nullable=False)

    def __str__(self):
        return self.name