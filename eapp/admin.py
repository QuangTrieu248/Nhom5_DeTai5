from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user
from flask import redirect, url_for, request
from eapp import app, db
from eapp.models import User, Airport, Airplane, FlightRoute, Flight, FlightSegment, UserRole


class MyAdminIndexView(AdminIndexView):
    @expose('/')
    def index(self):
        return self.render('admin/index.html')

    def is_accessible(self):
        return current_user.is_authenticated and current_user.user_role == UserRole.ADMIN

    def inaccessible_callback(self, name, **kwargs):
        return redirect('/login?next=' + request.url)


class AuthenticatedModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.user_role == UserRole.ADMIN

    def inaccessible_callback(self, name, **kwargs):
        return redirect('/login?next=' + request.url)


class AirportView(AuthenticatedModelView):
    column_list = ['id', 'name', 'address']
    column_searchable_list = ['name', 'address']


class FlightView(AuthenticatedModelView):
    column_searchable_list = ['id']
    can_export = True


admin = Admin(
    app=app,
    name='PLANEPLAN ADMIN',
    index_view=MyAdminIndexView()
)

admin.add_view(AirportView(Airport, db.session, name='Sân bay', endpoint='airport'))
admin.add_view(AuthenticatedModelView(Airplane, db.session, name='Máy bay', endpoint='airplane'))
admin.add_view(AuthenticatedModelView(FlightRoute, db.session, name='Tuyến bay', endpoint='flightroute'))
admin.add_view(FlightView(Flight, db.session, name='Chuyến bay', endpoint='flight'))
admin.add_view(AuthenticatedModelView(FlightSegment, db.session, name='Chặng bay', endpoint='flightsegment'))
admin.add_view(AuthenticatedModelView(User, db.session, name='Người dùng', endpoint='user'))