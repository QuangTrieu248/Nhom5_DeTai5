from flask_admin import Admin, AdminIndexView, expose,BaseView, expose
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user
from flask import redirect, request
from wtforms.validators import ValidationError
from eapp import app, db, dao
from eapp.models import (
    User, Airport, Airline, Airplane, FlightRoute,
    Flight, FlightSegment, Regulation, UserRole
)
from datetime import datetime



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


class UserView(AuthenticatedModelView):
    column_list = ['id', 'name', 'username', 'phone', 'user_role']
    column_searchable_list = ['name', 'username', 'phone']
    column_filters = ['user_role']
    form_excluded_columns = ['password', 'tickets']


class AirportView(AuthenticatedModelView):
    column_list = ['id', 'name', 'address']
    column_searchable_list = ['name', 'address']

    def on_model_change(self, form, model, is_created):
        if is_created:
            reg = Regulation.query.first()
            max_airports = reg.max_airports if reg else 10
            if Airport.query.count() >= max_airports:
                raise ValidationError(f'Hệ thống chỉ cho phép tối đa {max_airports} sân bay theo quy định!')


class FlightRouteView(AuthenticatedModelView):
    column_list = ['id', 'name', 'airline']
    column_searchable_list = ['name']


class FlightView(AuthenticatedModelView):
    column_list = ['id', 'flight_code', 'base_price', 'flight_route', 'airline']
    column_searchable_list = ['flight_code']
    can_export = True


class RegulationView(AuthenticatedModelView):
    can_create = False
    can_delete = False
    column_labels = {
        'max_airports': 'Số sân bay tối đa',
        'min_flight_time': 'Thời gian bay tối thiểu (phút)',
        'max_intermediate_airports': 'Số sân bay trung gian tối đa',
        'min_stop_time': 'Thời gian dừng tối thiểu (phút)',
        'max_stop_time': 'Thời gian dừng tối đa (phút)',
        'ticket_sale_deadline': 'Thời gian bán vé trước (giờ)',
        'booking_deadline': 'Thời gian đặt vé trước (giờ)',
        'economy_multiplier': 'Hệ số giá Phổ thông',
        'business_multiplier': 'Hệ số giá Thương gia'
    }


admin = Admin(
    app=app,
    name='PLANEPLAN ADMIN',
    index_view=MyAdminIndexView()
)

class StatsView(BaseView):
    @expose('/')
    def index(self):
        now = datetime.now()
        month = request.args.get('month', default=now.month, type=int)
        year = request.args.get('year', default=now.year, type=int)

        stats, total_revenue = dao.get_monthly_route_stats(month=month, year=year)
        return self.render(
            'admin/stats.html',
            month=month,
            year=year,
            stats=stats,
            total_revenue=total_revenue
        )

    def is_accessible(self):
        return current_user.is_authenticated and current_user.user_role == UserRole.ADMIN

admin.add_view(AirportView(Airport, db.session, name='Sân bay', endpoint='airport'))
admin.add_view(AuthenticatedModelView(Airline, db.session, name='Hãng bay', endpoint='airline'))
admin.add_view(AuthenticatedModelView(Airplane, db.session, name='Máy bay', endpoint='airplane'))
admin.add_view(FlightRouteView(FlightRoute, db.session, name='Tuyến bay', endpoint='flightroute'))
admin.add_view(FlightView(Flight, db.session, name='Chuyến bay', endpoint='flight'))
admin.add_view(AuthenticatedModelView(FlightSegment, db.session, name='Chặng bay', endpoint='flightsegment'))
admin.add_view(RegulationView(Regulation, db.session, name='Quy định', endpoint='regulation'))
admin.add_view(UserView(User, db.session, name='Người dùng', endpoint='user'))
admin.add_view(StatsView(name='Thống kê doanh thu', endpoint='stats'))