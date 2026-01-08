from flask import Flask, redirect, url_for, request, render_template, flash, session, abort
import mysql.connector
from flask_session import Session
from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import generate_password_hash, check_password_hash

from key import secret_key, salt, salt2
from stoken import token
from cmail import sendmail

# ---------------- APP CONFIG ---------------- #
app = Flask(__name__)
app.secret_key = secret_key
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# ---------------- DATABASE ---------------- #
mydb = mysql.connector.connect(
    host="localhost",
    user="root",
    password="admin",
    database="visitors"
)

# ---------------- HOME ---------------- #
@app.route('/')
def admin():
    return render_template('title.html')


# ---------------- ADMIN LOGIN ---------------- #
@app.route('/adminlogin', methods=['GET', 'POST'])
def adminlogin():
    if session.get('admin'):
        return redirect(url_for('adminhome'))

    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']

        cursor = mydb.cursor(buffered=True)
        cursor.execute('SELECT password FROM admin WHERE username=%s', [name])
        row = cursor.fetchone()
        cursor.close()

        if row and check_password_hash(row[0], password):
            session['admin'] = name
            return redirect(url_for('adminhome'))
        else:
            flash('Invalid username or password')

    return render_template('login.html')


# ---------------- ADMIN HOME ---------------- #
@app.route('/adminhome')
def adminhome():
    if not session.get('admin'):
        return redirect(url_for('adminlogin'))
    return render_template('homepage.html')


# ---------------- REGISTRATION ---------------- #
@app.route('/registration', methods=['GET', 'POST'])
def registration():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']

        cursor = mydb.cursor(buffered=True)
        cursor.execute('SELECT COUNT(*) FROM admin WHERE username=%s', [username])
        count_user = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM admin WHERE email=%s', [email])
        count_email = cursor.fetchone()[0]
        cursor.close()

        if count_user:
            flash('Username already exists')
        elif count_email:
            flash('Email already exists')
        else:
            hashed_password = generate_password_hash(password)

            data = {
                'username': username,
                'password': hashed_password,
                'email': email
            }

            confirm_link = url_for('confirm', token=token(data, salt), _external=True)
            body = f"Thanks for registering!\n\nClick to confirm:\n{confirm_link}"

            sendmail(email, 'Email Confirmation', body)
            flash('Confirmation link sent to your email')

    return render_template('registration.html')


# ---------------- EMAIL CONFIRM ---------------- #
@app.route('/confirm/<token>')
def confirm(token):
    try:
        serializer = URLSafeTimedSerializer(secret_key)
        data = serializer.loads(token, salt=salt, max_age=600)
    except:
        return 'Link expired. Please register again.'

    cursor = mydb.cursor(buffered=True)
    cursor.execute('SELECT COUNT(*) FROM admin WHERE username=%s', [data['username']])

    if cursor.fetchone()[0] == 0:
        cursor.execute(
            'INSERT INTO admin (username, password, email) VALUES (%s, %s, %s)',
            [data['username'], data['password'], data['email']]
        )
        mydb.commit()
        flash('Registration successful. Please login.')
    else:
        flash('Account already verified.')

    cursor.close()
    return redirect(url_for('adminlogin'))


# ---------------- FORGOT PASSWORD ---------------- #
@app.route('/forget', methods=['GET', 'POST'])
def forgot():
    if request.method == 'POST':
        email = request.form['email']

        cursor = mydb.cursor(buffered=True)
        cursor.execute('SELECT COUNT(*) FROM admin WHERE email=%s', [email])
        count = cursor.fetchone()[0]
        cursor.close()

        if count:
            reset_link = url_for('reset', token=token(email, salt2), _external=True)
            body = f"Click to reset password:\n{reset_link}"

            sendmail(email, 'Password Reset', body)
            flash('Password reset link sent')
            return redirect(url_for('adminlogin'))
        else:
            flash('Invalid email')

    return render_template('forgot.html')


# ---------------- RESET PASSWORD ---------------- #
@app.route('/reset/<token>', methods=['GET', 'POST'])
def reset(token):
    try:
        serializer = URLSafeTimedSerializer(secret_key)
        email = serializer.loads(token, salt=salt2, max_age=600)
    except:
        abort(404, 'Link expired')

    if request.method == 'POST':
        newpassword = request.form['npassword']
        confirmpassword = request.form['cpassword']

        if newpassword == confirmpassword:
            hashed_password = generate_password_hash(newpassword)

            cursor = mydb.cursor(buffered=True)
            cursor.execute(
                'UPDATE admin SET password=%s WHERE email=%s',
                [hashed_password, email]
            )
            mydb.commit()
            cursor.close()

            flash('Password updated successfully')
            return redirect(url_for('adminlogin'))
        else:
            flash('Passwords do not match')

    return render_template('newpassword.html')


# ---------------- LOGOUT ---------------- #
@app.route('/logout')
def logout():
    session.pop('admin', None)
    flash('Logged out successfully')
    return redirect(url_for('adminlogin'))


# ---------------- ADD USER ---------------- #
@app.route('/adduser', methods=['GET', 'POST'])
def adduser():
    if not session.get('admin'):
        return redirect(url_for('adminlogin'))

    if request.method == 'POST':
        fullname = request.form['name']
        mobile = request.form['mobile']
        room = request.form['room']

        cursor = mydb.cursor(buffered=True)
        cursor.execute(
            'SELECT COUNT(*) FROM users WHERE fullname=%s AND room=%s',
            [fullname, room]
        )

        if cursor.fetchone()[0]:
            flash('User already exists')
            cursor.close()
            return redirect(url_for('adduser'))

        cursor.execute(
            'INSERT INTO users (fullname, room, mobile) VALUES (%s, %s, %s)',
            [fullname, room, mobile]
        )
        mydb.commit()
        cursor.close()

        flash('User added successfully')
        return redirect(url_for('visitor'))

    return render_template('Add-Users.html')


# ---------------- VISITOR RECORD ---------------- #
@app.route('/visitor', methods=['GET', 'POST'])
def visitor():
    if not session.get('admin'):
        return redirect(url_for('adminlogin'))

    if request.method == 'POST':
        uid = request.form['id']
        name = request.form['name']
        mobile = request.form['mobile']

        cursor = mydb.cursor(buffered=True)
        cursor.execute(
            'INSERT INTO visitors (uid, vname, phno) VALUES (%s, %s, %s)',
            [uid, name, mobile]
        )
        mydb.commit()
        cursor.close()

        flash('Visitor added successfully')
        return redirect(url_for('visitor'))

    cursor = mydb.cursor(buffered=True)
    cursor.execute('SELECT uid, fullname FROM users')
    users = cursor.fetchall()

    cursor.execute('SELECT * FROM visitors ORDER BY vid DESC')
    visitors = cursor.fetchall()
    cursor.close()

    return render_template('VisitorRecord.html', data=users, details=visitors)


# ---------------- CHECK-IN / CHECK-OUT ---------------- #
@app.route('/checkinvisitor/<int:vid>')
def checkinvisitor(vid):
    if not session.get('admin'):
        return redirect(url_for('adminlogin'))

    cursor = mydb.cursor(buffered=True)
    cursor.execute('UPDATE visitors SET checkin=CURRENT_TIMESTAMP WHERE vid=%s', [vid])
    mydb.commit()
    cursor.close()

    return redirect(url_for('visitor'))


@app.route('/checkoutvisitor/<int:vid>')
def checkoutvisitor(vid):
    if not session.get('admin'):
        return redirect(url_for('adminlogin'))

    cursor = mydb.cursor(buffered=True)
    cursor.execute('UPDATE visitors SET checkout=CURRENT_TIMESTAMP WHERE vid=%s', [vid])
    mydb.commit()
    cursor.close()

    return redirect(url_for('visitor'))


# ---------------- RUN ---------------- #
if __name__ == '__main__':
    app.run(debug=True)