from flask import render_template
from eapp import app, dao

@app.route('/')
def home_view():
    return render_template('homepage.html')

@app.route('/staffpage')
def staff_view():
    return render_template('staffpage.html')

# @app.route('/flightpage')
# def flight_page_view():
#     airport = dao.load_airport()
#     return render_template('flightpage.html', airport=airport)
@app.route('/flightpage')
def flight_page_view():
    airplane = dao.count_airplane()
    return render_template('flightpage.html', airplane=airplane)

@app.route('/search')
def flight_search():
    return render_template('homepage.html')

@app.route('/register')
def register_view():
    return render_template('register.html')

@app.route('/login')
def login_view():
    return render_template('login.html')

if __name__ == '__main__':
    app.run(debug=True)

    