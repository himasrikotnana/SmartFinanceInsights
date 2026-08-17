import sqlite3
from flask import Flask, render_template, request, redirect, session, send_file
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
app = Flask(__name__)
app.secret_key = "smartfinance"


# ---------------- DATABASE CONNECTION ---------------- #

def get_db_connection():
    conn = sqlite3.connect('finance.db')
    conn.row_factory = sqlite3.Row
    return conn


# ---------------- REGISTER ---------------- #

@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()

        conn.execute(
            '''
            INSERT INTO users(username,email,password)
            VALUES(?,?,?)
            ''',
            (username, email, password)
        )

        conn.commit()
        conn.close()

        return redirect('/')

    return render_template('register.html')


# ---------------- LOGIN ---------------- #

@app.route('/', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()

        user = conn.execute(
            '''
            SELECT * FROM users
            WHERE email=? AND password=?
            ''',
            (email, password)
        ).fetchone()

        conn.close()

        if user:

            session['user_id'] = user['id']
            session['username'] = user['username']

            return redirect('/dashboard')

        return "Invalid Email or Password"

    return render_template('login.html')


# ---------------- DASHBOARD ---------------- #
@app.route('/dashboard')
def dashboard():

    if 'user_id' not in session:
        return redirect('/')

    conn = get_db_connection()

    # ---------------- User Details ---------------- #

    user = conn.execute(
        '''
        SELECT username, email
        FROM users
        WHERE id=?
        ''',
        (session['user_id'],)
    ).fetchone()

    # ---------------- Total Income ---------------- #

    income = conn.execute(
        '''
        SELECT SUM(amount)
        FROM income
        WHERE user_id=?
        ''',
        (session['user_id'],)
    ).fetchone()[0]

    # ---------------- Total Expense ---------------- #

    expense = conn.execute(
        '''
        SELECT SUM(amount)
        FROM expenses
        WHERE user_id=?
        ''',
        (session['user_id'],)
    ).fetchone()[0]

    # ---------------- Budget ---------------- #

    budget = conn.execute(
        '''
        SELECT budget_amount
        FROM budget
        WHERE user_id=?
        ''',
        (session['user_id'],)
    ).fetchone()

    # ---------------- Expense by Category ---------------- #

    category_data = conn.execute(
        '''
        SELECT category, SUM(amount) AS total
        FROM expenses
        WHERE user_id=?
        GROUP BY category
        ''',
        (session['user_id'],)
    ).fetchall()

    labels = []
    values = []

    for item in category_data:
        labels.append(item['category'])
        values.append(item['total'])

    # ---------------- Recent Transactions ---------------- #

    recent_transactions = conn.execute(
        '''
        SELECT
            'Income' AS type,
            source AS name,
            amount,
            date
        FROM income
        WHERE user_id=?

        UNION ALL

        SELECT
            'Expense' AS type,
            category AS name,
            amount,
            date
        FROM expenses
        WHERE user_id=?

        ORDER BY date DESC
        LIMIT 5
        ''',
        (
            session['user_id'],
            session['user_id']
        )
    ).fetchall()

    # ---------------- Goal Progress ---------------- #

    goals = conn.execute(
        '''
        SELECT *
        FROM goals
        WHERE user_id=?
        ''',
        (session['user_id'],)
    ).fetchall()

    goal_progress = []

    for goal in goals:

        progress = 0

        if goal['target_amount'] > 0:
            progress = int(
                (goal['saved_amount'] /
                 goal['target_amount']) * 100
            )

        if progress > 100:
            progress = 100

        goal_progress.append({
            "goal_name": goal['goal_name'],
            "progress": progress
        })

    # ---------------- Upcoming Bills ---------------- #

    try:

        upcoming_bills = conn.execute(
            '''
            SELECT *
            FROM bill_reminders
            WHERE user_id=?
            ORDER BY due_date ASC
            LIMIT 5
            ''',
            (session['user_id'],)
        ).fetchall()

    except:

        upcoming_bills = []

    # ---------------- Calculations ---------------- #

    total_income = income if income else 0
    total_expense = expense if expense else 0
    total_savings = total_income - total_expense

    budget_amount = 0

    if budget:
        budget_amount = budget['budget_amount']

    budget_percent = 0

    if budget_amount > 0:
        budget_percent = int(
            (total_expense / budget_amount) * 100
        )

    # ---------------- Notifications ---------------- #

    notifications = []

    if budget_percent >= 100:

        notifications.append(
            "⚠️ You have exceeded your monthly budget."
        )

    elif budget_percent >= 80:

        notifications.append(
            "⚠️ You have used more than 80% of your budget."
        )

    else:

        notifications.append(
            "✅ Your budget is under control."
        )

    if total_savings > 0:

        notifications.append(
            f"💰 Great! You saved ₹{total_savings:.2f} this month."
        )

    else:

        notifications.append(
            "⚠️ Your expenses are greater than your income."
        )

    # ---------------- Achievement Badges ---------------- #

    badges = []

    if total_savings >= 10000:
        badges.append("🏆 Super Saver")

    if budget_percent < 80:
        badges.append("💰 Budget Master")

    if total_income >= 100000:
        badges.append("📈 Wealth Builder")

    if len(goal_progress) > 0:
        badges.append("🎯 Goal Planner")

    if len(recent_transactions) >= 5:
        badges.append("🔥 Active User")

    conn.close()

    return render_template(
        'dashboard.html',
        username=session['username'],
        user=user,
        income=total_income,
        expense=total_expense,
        savings=total_savings,
        budget=budget_amount,
        budget_percent=budget_percent,
        labels=labels,
        values=values,
        notifications=notifications,
        recent_transactions=recent_transactions,
        goal_progress=goal_progress,
        upcoming_bills=upcoming_bills,
        badges=badges
    )
# ---------------- INCOME ---------------- #

@app.route('/income', methods=['GET', 'POST'])
def income():

    if 'user_id' not in session:
        return redirect('/')

    conn = get_db_connection()

    if request.method == 'POST':

        source = request.form['source']
        amount = request.form['amount']
        date = request.form['date']

        conn.execute(
            '''
            INSERT INTO income
            (user_id,source,amount,date)
            VALUES(?,?,?,?)
            ''',
            (session['user_id'], source, amount, date)
        )

        conn.commit()

    incomes = conn.execute(
        '''
        SELECT *
        FROM income
        WHERE user_id=?
        ''',
        (session['user_id'],)
    ).fetchall()

    conn.close()

    return render_template(
        'income.html',
        incomes=incomes
    )


# ---------------- EXPENSE ---------------- #

@app.route('/expense', methods=['GET', 'POST'])
def expense():

    if 'user_id' not in session:
        return redirect('/')

    conn = get_db_connection()

    # ---------- Add New Expense ----------

    if request.method == 'POST':

        category = request.form['category']
        amount = request.form['amount']
        date = request.form['date']

        conn.execute(
            '''
            INSERT INTO expenses
            (user_id, category, amount, date)
            VALUES (?, ?, ?, ?)
            ''',
            (session['user_id'], category, amount, date)
        )

        conn.commit()

    # ---------- Search Expense ----------

    search = request.args.get('search', '')

    if search:

        expenses = conn.execute(
            '''
            SELECT *
            FROM expenses
            WHERE user_id=?
            AND category LIKE ?
            ''',
            (
                session['user_id'],
                '%' + search + '%'
            )
        ).fetchall()

    else:

        expenses = conn.execute(
            '''
            SELECT *
            FROM expenses
            WHERE user_id=?
            ''',
            (session['user_id'],)
        ).fetchall()

    conn.close()

    return render_template(
        'expenditure.html',
        expenses=expenses
    )

# ---------------- BUDGET ---------------- #

@app.route('/budget', methods=['GET', 'POST'])
def budget():

    if 'user_id' not in session:
        return redirect('/')

    conn = get_db_connection()

    if request.method == 'POST':

        amount = request.form['budget']

        old_budget = conn.execute(
            '''
            SELECT *
            FROM budget
            WHERE user_id=?
            ''',
            (session['user_id'],)
        ).fetchone()

        if old_budget:

            conn.execute(
                '''
                UPDATE budget
                SET budget_amount=?
                WHERE user_id=?
                ''',
                (amount, session['user_id'])
            )

        else:

            conn.execute(
                '''
                INSERT INTO budget
                (user_id,budget_amount)
                VALUES(?,?)
                ''',
                (session['user_id'], amount)
            )

        conn.commit()

    budget_data = conn.execute(
        '''
        SELECT *
        FROM budget
        WHERE user_id=?
        ''',
        (session['user_id'],)
    ).fetchone()

    conn.close()

    return render_template(
        'budget.html',
        budget=budget_data
    )
# ------------------PORTFOLIO-------------------#
@app.route('/portfolio', methods=['GET', 'POST'])
def portfolio():

    if 'user_id' not in session:
        return redirect('/')

    conn = get_db_connection()

    if request.method == 'POST':

        asset_name = request.form['asset_name']
        category = request.form['category']
        invested_amount = request.form['invested_amount']
        current_value = request.form['current_value']
        purchase_date = request.form['purchase_date']

        conn.execute(
            '''
            INSERT INTO portfolio
            (user_id, asset_name, category, invested_amount, current_value, purchase_date)
            VALUES (?, ?, ?, ?, ?, ?)
            ''',
            (
                session['user_id'],
                asset_name,
                category,
                invested_amount,
                current_value,
                purchase_date
            )
        )

        conn.commit()

    portfolio = conn.execute(
        '''
        SELECT *
        FROM portfolio
        WHERE user_id=?
        ''',
        (session['user_id'],)
    ).fetchall()
    total_investment = sum(item['invested_amount'] for item in portfolio)
    current_value = sum(item['current_value'] for item in portfolio)

    profit = current_value - total_investment

    roi = 0
    if total_investment > 0:
        roi = round((profit / total_investment) * 100, 2)

    conn.close()

    return render_template(
    'portfolio.html',
    portfolio=portfolio,
    total_investment=total_investment,
    current_value=current_value,
    profit=profit,
    roi=roi
)
#-----------------------GOALS--------------------------#
@app.route('/goals', methods=['GET', 'POST'])
def goals():

    if 'user_id' not in session:
        return redirect('/')

    conn = get_db_connection()

    if request.method == 'POST':

        goal_name = request.form['goal_name']
        target_amount = float(request.form['target_amount'])
        saved_amount = float(request.form['saved_amount'])
        target_date = request.form['target_date']

        conn.execute(
            '''
            INSERT INTO goals
            (user_id, goal_name, target_amount, saved_amount, target_date)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (
                session['user_id'],
                goal_name,
                target_amount,
                saved_amount,
                target_date
            )
        )

        conn.commit()

    goals = conn.execute(
        '''
        SELECT *
        FROM goals
        WHERE user_id=?
        ''',
        (session['user_id'],)
    ).fetchall()

    goal_data = []

    for goal in goals:

        progress = 0

        if goal['target_amount'] > 0:
            progress = int(
                (goal['saved_amount'] / goal['target_amount']) * 100
            )

        remaining = goal['target_amount'] - goal['saved_amount']

        if goal['saved_amount'] >= goal['target_amount']:
            status = "Completed"
        else:
            status = "In Progress"

        goal_data.append({
            "goal_name": goal["goal_name"],
            "target_amount": goal["target_amount"],
            "saved_amount": goal["saved_amount"],
            "target_date": goal["target_date"],
            "progress": progress,
            "remaining": remaining,
            "status": status
        })

    conn.close()

    return render_template(
        'goals.html',
        goals=goal_data
    )
#-----------------------ANALYTICS-------------------#
@app.route('/analytics')
def analytics():

    if 'user_id' not in session:
        return redirect('/')

    conn = get_db_connection()

    portfolio = conn.execute(
        '''
        SELECT *
        FROM portfolio
        WHERE user_id=?
        ''',
        (session['user_id'],)
    ).fetchall()

    conn.close()

    total_investment = sum(item['invested_amount'] for item in portfolio)
    current_value = sum(item['current_value'] for item in portfolio)

    profit = current_value - total_investment

    roi = 0

    if total_investment > 0:
        roi = round((profit / total_investment) * 100, 2)

    stocks = 0
    mutual = 0
    gold = 0
    fd = 0
    bonds = 0
    realestate = 0
    crypto = 0

    for item in portfolio:
        category = item['category'].strip().lower()

        if category == "stocks":
            stocks += item['current_value']

        elif category == "mutual funds":
            mutual += item['current_value']

        elif category == "gold":
            gold += item['current_value']

        elif category == "fixed deposits":
            fd += item['current_value']

        elif category == "bonds":
            bonds += item['current_value']

        elif category == "real estate":
            realestate += item['current_value']

        elif category == "cryptocurrency":
            crypto += item['current_value']
    print(portfolio)
    return render_template(
        'analytics.html',
        total=total_investment,
        current=current_value,
        profit=profit,
        roi=roi,
        stocks=stocks,
        mutual=mutual,
        gold=gold,
        fd=fd,
        bonds=bonds,
        realestate=realestate,
        crypto=crypto,
        portfolio=portfolio
    )
# ---------------- PROFILE ---------------- #

@app.route('/profile', methods=['GET', 'POST'])
def profile():

    if 'user_id' not in session:
        return redirect('/')

    conn = get_db_connection()

    if request.method == 'POST':

        phone = request.form['phone']
        dob = request.form['dob']
        occupation = request.form['occupation']
        monthly_income = request.form['monthly_income']
        risk_level = request.form['risk_level']

        existing = conn.execute(
            '''
            SELECT *
            FROM profile
            WHERE user_id=?
            ''',
            (session['user_id'],)
        ).fetchone()

        if existing:

            conn.execute(
                '''
                UPDATE profile
                SET phone=?,
                    dob=?,
                    occupation=?,
                    monthly_income=?,
                    risk_level=?
                WHERE user_id=?
                ''',
                (
                    phone,
                    dob,
                    occupation,
                    monthly_income,
                    risk_level,
                    session['user_id']
                )
            )

        else:

            conn.execute(
                '''
                INSERT INTO profile
                (user_id, phone, dob, occupation, monthly_income, risk_level)
                VALUES (?, ?, ?, ?, ?, ?)
                ''',
                (
                    session['user_id'],
                    phone,
                    dob,
                    occupation,
                    monthly_income,
                    risk_level
                )
            )

        conn.commit()

    profile = conn.execute(
        '''
        SELECT *
        FROM profile
        WHERE user_id=?
        ''',
        (session['user_id'],)
    ).fetchone()

    conn.close()

    return render_template(
        'profile.html',
        profile=profile,
        username=session['username']
    )
# ---------------- BILL REMINDER ---------------- #

@app.route('/bills', methods=['GET', 'POST'])
def bills():

    if 'user_id' not in session:
        return redirect('/')

    conn = get_db_connection()

    if request.method == 'POST':

        bill_name = request.form['bill_name']
        amount = request.form['amount']
        due_date = request.form['due_date']
        status = request.form['status']

        conn.execute(
            '''
            INSERT INTO bills
            (user_id, bill_name, amount, due_date, status)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (
                session['user_id'],
                bill_name,
                amount,
                due_date,
                status
            )
        )

        conn.commit()

    bills = conn.execute(
        '''
        SELECT *
        FROM bills
        WHERE user_id=?
        ORDER BY due_date
        ''',
        (session['user_id'],)
    ).fetchall()

    conn.close()

    return render_template(
        'bill_reminder.html',
        bills=bills
    )

# ---------------- EXPORT PDF ---------------- #

@app.route('/export_pdf')
def export_pdf():

    if 'user_id' not in session:
        return redirect('/')

    conn = get_db_connection()

    income = conn.execute(
        '''
        SELECT SUM(amount)
        FROM income
        WHERE user_id=?
        ''',
        (session['user_id'],)
    ).fetchone()[0] or 0

    expense = conn.execute(
        '''
        SELECT SUM(amount)
        FROM expenses
        WHERE user_id=?
        ''',
        (session['user_id'],)
    ).fetchone()[0] or 0

    conn.close()

    savings = income - expense

    filename = "Finance_Report.pdf"

    doc = SimpleDocTemplate(filename)

    styles = getSampleStyleSheet()

    story = []

    story.append(Paragraph("<b>SMART FINANCE INSIGHTS</b>", styles['Title']))
    story.append(Paragraph("<br/>", styles['Normal']))

    story.append(Paragraph(f"User : {session['username']}", styles['Heading2']))
    story.append(Paragraph(f"Total Income : ₹{income}", styles['Normal']))
    story.append(Paragraph(f"Total Expense : ₹{expense}", styles['Normal']))
    story.append(Paragraph(f"Total Savings : ₹{savings}", styles['Normal']))

    doc.build(story)

    return send_file(
        filename,
        as_attachment=True
    )
# ---------------- REPORTS ---------------- #
@app.route('/reports')
def reports():

    if 'user_id' not in session:
        return redirect('/')

    conn = get_db_connection()

    income = conn.execute(
        '''
        SELECT SUM(amount)
        FROM income
        WHERE user_id=?
        ''',
        (session['user_id'],)
    ).fetchone()[0]

    expense = conn.execute(
        '''
        SELECT SUM(amount)
        FROM expenses
        WHERE user_id=?
        ''',
        (session['user_id'],)
    ).fetchone()[0]

    conn.close()

    income = income if income else 0
    expense = expense if expense else 0
    savings = income - expense

    return render_template(
        'reports.html',
        income=income,
        expense=expense,
        savings=savings
    )


# ---------------- AI INSIGHTS ---------------- #
# ---------------- AI INSIGHTS ---------------- #

@app.route('/insights')
def insights():

    if 'user_id' not in session:
        return redirect('/')

    conn = get_db_connection()

    # Income
    income = conn.execute(
        '''
        SELECT SUM(amount)
        FROM income
        WHERE user_id=?
        ''',
        (session['user_id'],)
    ).fetchone()[0] or 0

    # Expenses
    expense = conn.execute(
        '''
        SELECT SUM(amount)
        FROM expenses
        WHERE user_id=?
        ''',
        (session['user_id'],)
    ).fetchone()[0] or 0

    # Budget
    budget = conn.execute(
        '''
        SELECT budget_amount
        FROM budget
        WHERE user_id=?
        ''',
        (session['user_id'],)
    ).fetchone()

    # Portfolio
    portfolio = conn.execute(
        '''
        SELECT SUM(invested_amount) AS invested,
               SUM(current_value) AS current
        FROM portfolio
        WHERE user_id=?
        ''',
        (session['user_id'],)
    ).fetchone()

    # Goals
    goals = conn.execute(
        '''
        SELECT *
        FROM goals
        WHERE user_id=?
        ''',
        (session['user_id'],)
    ).fetchall()

    conn.close()

    insights = []

    savings = income - expense

    # Savings Insight
    if savings > 0:
        insights.append(f"💰 Great! You saved ₹{savings:.2f} this month.")
    else:
        insights.append("⚠️ Your expenses are higher than your income.")

    # Budget Insight
    if budget:

        budget_amount = budget['budget_amount']

        percent = (expense / budget_amount) * 100 if budget_amount > 0 else 0

        if percent >= 100:
            insights.append("🚨 You have exceeded your monthly budget.")

        elif percent >= 80:
            insights.append(f"⚠️ You have used {percent:.0f}% of your budget.")

        else:
            insights.append(f"✅ Budget usage is only {percent:.0f}%.")

    # Portfolio Insight
    invested = portfolio['invested'] or 0
    current = portfolio['current'] or 0

    if invested > 0:

        profit = current - invested

        if profit > 0:
            insights.append(f"📈 Your investments gained ₹{profit:.2f}.")
        elif profit < 0:
            insights.append(f"📉 Your investments are down by ₹{abs(profit):.2f}.")
        else:
            insights.append("📊 Your investments are stable.")

    # Goal Insight
    completed = 0

    for goal in goals:
        if goal['saved_amount'] >= goal['target_amount']:
            completed += 1

    if len(goals) > 0:
        insights.append(
            f"🎯 You have completed {completed} out of {len(goals)} financial goals."
        )
    else:
        insights.append("🎯 Start adding financial goals to track your progress.")

    # Health Score
    if income > 0:
        score = int((savings / income) * 100)
    else:
        score = 0

    if score >= 70:
        insights.append("❤️ Your financial health is Excellent.")

    elif score >= 40:
        insights.append("💙 Your financial health is Good.")

    else:
        insights.append("⚠️ Improve your savings to increase your financial health score.")

    return render_template(
        'insights.html',
        insights=insights
    )

# ---------------- HEALTH SCORE ---------------- #

@app.route('/health')
def health():

    if 'user_id' not in session:
        return redirect('/')

    conn = get_db_connection()

    income = conn.execute(
        '''
        SELECT SUM(amount)
        FROM income
        WHERE user_id=?
        ''',
        (session['user_id'],)
    ).fetchone()[0]

    expense = conn.execute(
        '''
        SELECT SUM(amount)
        FROM expenses
        WHERE user_id=?
        ''',
        (session['user_id'],)
    ).fetchone()[0]

    conn.close()

    income = income if income else 0
    expense = expense if expense else 0

    savings = income - expense

    score = 0

    if income > 0:
        score = int((savings / income) * 100)

    return render_template(
        'health_score.html',
        score=score
    )
#-----------------calender--------------------#
@app.route('/calendar')
def calendar():

    if 'user_id' not in session:
        return redirect('/')

    conn = get_db_connection()

    bills = conn.execute(
        '''
        SELECT bill_name,
               due_date
        FROM bill_reminders
        WHERE user_id=?
        ORDER BY due_date
        ''',
        (session['user_id'],)
    ).fetchall()

    goals = conn.execute(
        '''
        SELECT goal_name,
               target_date
        FROM goals
        WHERE user_id=?
        ORDER BY target_date
        ''',
        (session['user_id'],)
    ).fetchall()

    conn.close()

    return render_template(
        "calendar.html",
        bills=bills,
        goals=goals
    )
# ---------------- SETTINGS ---------------- #

@app.route('/settings', methods=['GET', 'POST'])
def settings():

    if 'user_id' not in session:
        return redirect('/')

    conn = get_db_connection()

    user = conn.execute(
        '''
        SELECT *
        FROM users
        WHERE id=?
        ''',
        (session['user_id'],)
    ).fetchone()

    message = ""

    if request.method == 'POST':

        username = request.form['username']
        email = request.form['email']

        conn.execute(
            '''
            UPDATE users
            SET username=?, email=?
            WHERE id=?
            ''',
            (
                username,
                email,
                session['user_id']
            )
        )

        conn.commit()

        session['username'] = username

        message = "Profile updated successfully."

        user = conn.execute(
            '''
            SELECT *
            FROM users
            WHERE id=?
            ''',
            (session['user_id'],)
        ).fetchone()

    conn.close()

    return render_template(
        'settings.html',
        user=user,
        message=message
    )
#------------------change password------------#
@app.route('/change_password', methods=['GET', 'POST'])
def change_password():

    if 'user_id' not in session:
        return redirect('/')

    conn = get_db_connection()

    if request.method == 'POST':

        new_password = request.form['new_password']

        conn.execute(
            '''
            UPDATE users
            SET password=?
            WHERE id=?
            ''',
            (new_password, session['user_id'])
        )

        conn.commit()
        conn.close()

        return redirect('/settings')

    conn.close()

    return render_template('change_password.html')
# ---------------- FEEDBACK ---------------- #

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():

    if 'user_id' not in session:
        return redirect('/')

    conn = get_db_connection()

    if request.method == 'POST':

        rating = int(request.form['rating'])
        message = request.form['message']

        conn.execute(
            '''
            INSERT INTO feedback
            (user_id, rating, message, created_at)
            VALUES (?, ?, ?, datetime('now'))
            ''',
            (
                session['user_id'],
                rating,
                message
            )
        )

        conn.commit()
        conn.close()

        return redirect('/feedback')

    feedback_data = conn.execute(
        '''
        SELECT *
        FROM feedback
        WHERE user_id=?
        ORDER BY created_at DESC
        ''',
        (session['user_id'],)
    ).fetchall()

    conn.close()

    return render_template(
        'feedback.html',
        feedback=feedback_data
    )
@app.route('/jarvis', methods=['GET', 'POST'])
def jarvis():

    if 'user_id' not in session:
        return redirect('/')

    conn = get_db_connection()

    user_id = session['user_id']

    answer = None

    # ---------------- TOTAL INCOME ---------------- #

    income_result = conn.execute(
        '''
        SELECT SUM(amount)
        FROM income
        WHERE user_id=?
        ''',
        (user_id,)
    ).fetchone()

    total_income = income_result[0] if income_result[0] else 0


    # ---------------- TOTAL EXPENSE ---------------- #

    expense_result = conn.execute(
        '''
        SELECT SUM(amount)
        FROM expenses
        WHERE user_id=?
        ''',
        (user_id,)
    ).fetchone()

    total_expense = expense_result[0] if expense_result[0] else 0


    # ---------------- BUDGET ---------------- #

    budget_result = conn.execute(
        '''
        SELECT budget_amount
        FROM budget
        WHERE user_id=?
        ''',
        (user_id,)
    ).fetchone()

    if budget_result:
        total_budget = budget_result['budget_amount']
    else:
        total_budget = 0


    # ---------------- SAVINGS ---------------- #

    total_savings = total_income - total_expense


    # ---------------- GOALS ---------------- #

    goals = conn.execute(
        '''
        SELECT goal_name, target_amount, saved_amount
        FROM goals
        WHERE user_id=?
        ''',
        (user_id,)
    ).fetchall()


    # ---------------- BILLS ---------------- #

    try:

        upcoming_bills = conn.execute(
            '''
            SELECT bill_name, amount, due_date
            FROM bill_reminders
            WHERE user_id=?
            ORDER BY due_date ASC
            LIMIT 5
            ''',
            (user_id,)
        ).fetchall()

    except sqlite3.OperationalError:

        upcoming_bills = []


    # ---------------- JARVIS QUESTIONS ---------------- #

    if request.method == 'POST':

        question = request.form.get('question', '').lower().strip()


        # -------- INCOME -------- #

        if 'income' in question:

            answer = (
                f"💰 Your total income is "
                f"₹{total_income:.2f}."
            )


        # -------- EXPENSE -------- #

        elif 'expense' in question or 'expenses' in question:

            answer = (
                f"💸 Your total expenses are "
                f"₹{total_expense:.2f}."
            )


        # -------- SAVINGS -------- #

        elif 'saving' in question or 'savings' in question:

            if total_savings > 0:

                answer = (
                    f"💰 You have saved "
                    f"₹{total_savings:.2f}."
                )

            else:

                answer = (
                    f"⚠️ Your expenses are greater than "
                    f"your income by ₹{abs(total_savings):.2f}."
                )


        # -------- BUDGET -------- #

        elif 'budget' in question:

            if total_budget > 0:

                percentage = (
                    total_expense / total_budget
                ) * 100

                answer = (
                    f"📊 Your budget is ₹{total_budget:.2f}.<br>"
                    f"You have used {percentage:.1f}% "
                    f"of your budget."
                )

            else:

                answer = (
                    "📊 You haven't set a budget yet."
                )


        # -------- GOALS -------- #

        elif 'goal' in question:

            if goals:

                answer = "🎯 Here are your financial goals:<br><br>"

                for goal in goals:

                    target = goal['target_amount']
                    saved = goal['saved_amount']

                    progress = 0

                    if target and target > 0:

                        progress = int(
                            (saved / target) * 100
                        )

                    if progress > 100:
                        progress = 100

                    answer += (
                        f"🎯 <strong>{goal['goal_name']}</strong><br>"
                        f"Saved: ₹{saved:.2f}<br>"
                        f"Target: ₹{target:.2f}<br>"
                        f"Progress: {progress}%<br><br>"
                    )

            else:

                answer = (
                    "🎯 You haven't added any financial "
                    "goals yet."
                )


        # -------- BILLS -------- #

        elif 'bill' in question or 'bills' in question:

            if upcoming_bills:

                answer = (
                    "🔔 Here are your upcoming bills:"
                    "<br><br>"
                )

                for bill in upcoming_bills:

                    answer += (
                        f"💳 <strong>{bill['bill_name']}</strong><br>"
                        f"Amount: ₹{bill['amount']:.2f}<br>"
                        f"Due date: {bill['due_date']}<br><br>"
                    )

            else:

                answer = (
                    "🔔 You don't have any upcoming "
                    "bills."
                )


        # -------- GENERAL QUESTION -------- #

        else:

            answer = (
                "🤖 I can help you with:<br><br>"
                "💰 Income<br>"
                "💸 Expenses<br>"
                "💵 Savings<br>"
                "📊 Budget<br>"
                "🎯 Financial Goals<br>"
                "🔔 Upcoming Bills"
            )


    conn.close()


    return render_template(
        'jarvis.html',
        username=session['username'],
        answer=answer
    )
# ---------------- LOGOUT ---------------- #

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


# ---------------- RUN APP ---------------- #

if __name__ == '__main__':
    app.run(debug=True)