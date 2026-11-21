from flask_admin import Admin
from eapp import app,db


admin = Admin(app=app, name='eCommerce Admin')
