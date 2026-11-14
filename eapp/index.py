from flask import Flask, render_template

app = Flask(__name__)
   # return render_template('homepage.html')

@app.route('/')
def home_view():
    return render_template('homepage.html')

@app.route('/staffpage')
def staff_view():
    return render_template('staffpage.html')

@app.route('/login')
def login_view():
    return render_template('login.html')

if __name__ == '__main__':
    app.run(debug=True)