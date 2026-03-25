from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from dotenv import load_dotenv
from auth import init_oauth, login_required
from db import get_or_create_user, save_expense, get_expenses, delete_expense, update_budget
from datetime import datetime
import logging
import os

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
app.config['GOOGLE_CLIENT_ID'] = os.getenv('GOOGLE_CLIENT_ID')
app.config['GOOGLE_CLIENT_SECRET'] = os.getenv('GOOGLE_CLIENT_SECRET')

logging.basicConfig(level=logging.DEBUG)

google = init_oauth(app)

@app.route('/')
@login_required
def index():
    user = session['user']
    expenses = get_expenses(user['google_id'])
    for e in expenses:
        e['_id'] = str(e['_id'])
    total = sum(e['amount'] for e in expenses)
    budget = user.get('monthly_budget', 0)
    current_month = datetime.utcnow().strftime('%Y-%m')
    monthly_total = sum(
        e['amount'] for e in expenses
        if e['date'].startswith(current_month)
    )
    return render_template('index.html',
                           expenses=expenses,
                           total=total,
                           user=user,
                           budget=budget,
                           monthly_total=monthly_total)

@app.route('/login')
def login():
    if 'user' in session:
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/auth/google')
def google_login():
    redirect_uri = url_for('google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/auth/google/callback')
def google_callback():
    token = google.authorize_access_token()
    userinfo = token['userinfo']
    user = get_or_create_user(
        google_id=userinfo['sub'],
        name=userinfo['name'],
        email=userinfo['email'],
        picture=userinfo.get('picture', '')
    )
    session['user'] = {
        'google_id': userinfo['sub'],
        'name': userinfo['name'],
        'email': userinfo['email'],
        'picture': userinfo.get('picture', ''),
        'monthly_budget': user.get('monthly_budget', 0)
    }
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        user = session['user']
        save_expense(
            user_id=user['google_id'],
            amount=request.form['amount'],
            category=request.form['category'],
            note=request.form['note'],
            date=request.form['date']
        )
        return redirect(url_for('index'))
    return render_template('add.html')

@app.route('/delete/<expense_id>', methods=['POST'])
@login_required
def delete(expense_id):
    delete_expense(expense_id)
    return redirect(url_for('index'))

@app.route('/stats')
@login_required
def stats():
    user = session['user']
    expenses = get_expenses(user['google_id'])
    for e in expenses:
        e['_id'] = str(e['_id'])
    categories = {}
    monthly = {}
    for e in expenses:
        categories[e['category']] = categories.get(e['category'], 0) + e['amount']
        month = e['date'][:7]
        monthly[month] = monthly.get(month, 0) + e['amount']
    return render_template('stats.html',
                           expenses=expenses,
                           categories=categories,
                           monthly=monthly,
                           user=user)

@app.route('/budget', methods=['POST'])
@login_required
def set_budget():
    user = session['user']
    budget = request.form['budget']
    update_budget(user['google_id'], budget)
    session['user']['monthly_budget'] = float(budget)
    return redirect(url_for('index'))

@app.route('/ping')
def ping():
    return jsonify({"status": "alive"})

@app.errorhandler(500)
def internal_error(error):
    import traceback
    return f"<pre>{traceback.format_exc()}</pre>", 500

if __name__ == '__main__':
    app.run(debug=True)
