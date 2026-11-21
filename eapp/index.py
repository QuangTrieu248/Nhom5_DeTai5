from flask import render_template
from eapp import app, dao

###
from eapp.models import Policy
from flask import flash, redirect

@app.route('/')
def home_view():
    return render_template('homepage.html')

@app.route('/staffpage')
def staff_view():
    return render_template('staff/staffpage.html')

@app.route('/search')
def flight_search():
    return render_template('homepage.html')

@app.route('/register')
def register_view():
    return render_template('register.html')

@app.route('/login')
def login_view():
    return render_template('login.html')

@app.route('/flightpage')
def flight_page_view():
    flight_ticket = dao.load_flight_tickect3()
    return render_template('flightpage.html', flight_ticket=flight_ticket)

@app.route('/flightselect')
def flight_select_view():
    flight_ticket = dao.seed_flight_data()
    return render_template('flightselect.html', flight_ticket=flight_ticket)

if __name__ == '__main__':
    from eapp.admin import *
    app.run(debug=True)

    