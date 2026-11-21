from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import quote
import cloudinary
from flask_login import LoginManager

app = Flask(__name__)
app.secret_key = 'planeplan_secret_key_nhom5'


app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:%s@localhost/planeplandb?charset=utf8mb4' % quote('123456')
#db local nen muon connect thi doi quote dong tren theo mk db trong may cua minh nha
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:%s@localhost/planeplandb?charset=utf8mb4' % quote('123456')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

db = SQLAlchemy(app=app)
login = LoginManager(app=app)

login = LoginManager(app)
login.login_view = 'login_view'

cloudinary.config(
    cloud_name='x2rmkazr',
    api_key='844616215888457',
    api_secret='S4PRbCucYfUF9-LBEkL5blSbS6Q'
)
