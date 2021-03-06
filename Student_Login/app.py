from flask import Flask, render_template, flash, redirect, url_for, session, logging, request,jsonify
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps

app = Flask(__name__)
#/home/mugdha/Projects/Library_Management_System/config.py
#app.config.from_pyfile('D:\4th sem\lab\Assignment 3-dbms\Library-Management-System/config.py')

app.config['MYSQL_HOST'] = '127.0.0.1'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '755435'
app.config['MYSQL_DB'] = 'library'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
# Initializing MySQL
mysql = MySQL(app)

@app.route('/')
def index():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

# Register Form Class
class RegisterForm(Form):
    studentName = StringField("Student Name", [validators.Length(min=1, max=100)])
    studentUsername = StringField('Username- Student ID number', [validators.Length(min=1, max=25)])
    email = StringField('Email', [validators.Length(min=1, max=50)])
    mobile = StringField("Mobile Number", [validators.Length(min=12, max=12)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match')
        ])
    confirm = PasswordField('Confirm Password')

#User Registration
@app.route('/register', methods=['GET', 'POST'])
def register():
        form = RegisterForm(request.form)
        if request.method == 'POST' and form.validate():
            studentName = form.studentName.data
            email = form.email.data
            mobile = form.mobile.data
            studentUsername = form.studentUsername.data
            password = sha256_crypt.encrypt(str(form.password.data))

            # Creating the cursor
            cur = mysql.connection.cursor()

            # Executing Query
            cur.execute("INSERT INTO students(studentName, email, mobile, studentUsername, password) VALUES(%s, %s, %s, %s, %s)", (studentName, email, mobile, studentUsername, password))


            # Commit to database
            mysql.connection.commit()

            # Close connection
            cur.close()

            flash("You are now registered.", 'success')

            return redirect(url_for('login'))

        return render_template('register.html', form= form )

# User Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':

        #Get form fields
        studentUsername = request.form['studentUsername']
        password_candidate = request.form['password']

        # Create Cursor
        cur = mysql.connection.cursor()

        # Get user by Username
        result = cur.execute("SELECT * FROM students WHERE studentUsername = %s", [studentUsername])

        if result > 0:

            # Get the stored hash
            data = cur.fetchone()
            password = data['password']

            # Comparing the Passwords
            if sha256_crypt.verify(password_candidate, password):

                # Password matched
                session['logged_in'] = True
                session['studentUsername'] = studentUsername
                session['student_id']= data['student_id']
                # session['aadharNo'] = data['aadharNo']

                flash('You have successfully logged in', 'success')
                return redirect(url_for('friends'))

            else:
                error = 'Invalid login.'
                return render_template('login.html', error = error)

            #Close connection
            cur.close()

        else:
            error = 'Username not found.'
            return render_template('login.html', error = error)

    return render_template('login.html')


@app.route('/friends',methods=['POST','GET'])
def friends():
    
    cur2 = mysql.connection.cursor()
    result2=cur2.execute("select students.studentName,students.student_id from students where student_id in (select from_user_id from friend where to_user_id=%s and request_status='accepted' union select to_user_id from friend where from_user_id=%s and request_status='accepted')",[session["student_id"],session["student_id"],])
    if request.method=='POST':
        friendid=request.form.get('friendid')
        session['friend']=friendid
        return redirect(url_for('friendbookshelf'))
    if result2 > 0:
        data=cur2.fetchall()
        return render_template('friends.html',friends=data,name=session["studentUsername"])
        cur2.close()

@app.route("/livesearch",methods=["POST","GET"])
def livesearch():
    searchbox = request.form.get("text")
    cursor = mysql.connection.cursor()
    query = "select studentName from students where studentName LIKE '{}%' order by studentName".format(searchbox)#This is just example query , you should replace field names with yours
    cursor.execute(query)
    result = cursor.fetchall()
    return jsonify(result)      

@app.route("/bookdetails/<id>",methods=["POST","GET"])
def bookdetails(id):
    cur = mysql.connection.cursor()
    result2=cur.execute("select * from books where book_id=%s",(id,))
    if result2>0:
        result2=cur.fetchall()
        return render_template('bookdetails.html',details=result2)
    
@app.route("/searchfriend",methods=["POST","GET"])
def searchfriend():
   if(request.method=='POST'):
        if request.form.get('friendname'):
            username = request.form.get('friendname')
            session['friend_name']=username
            cur2 = mysql.connection.cursor()
            result2=cur2.execute("select students.studentName,students.student_id from students where student_id in (select from_user_id from friend where to_user_id=%s and request_status='accepted' union select to_user_id from friend where from_user_id=%s and request_status='accepted')",[session["student_id"],session["student_id"],])
            if result2>0:
                data=cur2.fetchall()
                for friend in data :
                    if username in friend["studentName"]:
                        friendid=friend["student_id"]
                        session['friend']=friendid
                        return redirect(url_for('friendbookshelf'))
                cur2.close()
        cur2 = mysql.connection.cursor()
        result=cur2.execute("select student_id from students where studentName = %s", (session['friend_name'],))
        friendid=cur2.fetchall()
        friendid=friendid[0]['student_id']
        status='Send_request'
        result2=cur2.execute("select request_status from friend where from_user_id='%s' and to_user_id='%s'",(session['student_id'],friendid))
        if result2>0:
            status='Pending_request'
        result2=cur2.execute("select request_status from friend where to_user_id='%s' and from_user_id='%s'",(session['student_id'],friendid))
        if result2>0:
            status='Accept_request'
        if request.form.get('sendfriendrequest'):
            friendid=request.form.get('friendid')
            s=request.form.get('sendfriendrequest')
            if(s=='Send_request'):
                cur2.execute('insert into friend(from_user_id,to_user_id,request_status) values (%s,%s,%s)',(session['student_id'],friendid,'Pending'))
                mysql.connection.commit()
                status='Pending_request'  
            if(s=='Accept_request'):
                cur2.execute("update friend set request_status=%s where to_user_id=%s",('accepted',session['student_id']))
                mysql.connection.commit()
                session['friend']=friendid
                return redirect(url_for('friendbookshelf'))
        return render_template('searchfriend.html', name=session['friend_name'],friendid=friendid,status=status)
        
    
@app.route("/friendbookshelf",methods=["POST","GET"])
def friendbookshelf():
      cur = mysql.connection.cursor()
      result = cur.execute("SELECT s.studentName,b.user_id,b.book_id,b.bookshelf_date,c.bookName,c.author FROM students as s,user_bookshelf as b,books as c WHERE student_id = %s and user_id=%s and c.book_id=b.book_id", [session['friend'],session['friend']])
      if result>0:
          data=cur.fetchall()
          return render_template('bookshelf.html',books=data)
                                                                            

# Check if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args,**kwargs)
        else:
            flash('Unauthorized, please Login.', 'danger')
            return redirect(url_for('login'))
    return wrap

# Creating the Books list
@app.route('/bookslist')
# @is_logged_in
def bookslist():
    # Create Cursor
    cur = mysql.connection.cursor()
    # Execute
    result = cur.execute("SELECT bookName, count(bookName) AS count FROM books GROUP BY bookName")
    books = cur.fetchall()
    if result > 0:
        return render_template('bookslist.html', books = books)
    else:
        msg = 'No books found'
        return render_template('bookslist.html', msg= msg)
    # Close connection
    cur.close()

# Personal Details
@app.route('/student_detail')
@is_logged_in
def student_detail():

    # Create Cursor
    cur = mysql.connection.cursor()

    # Execute
    result = cur.execute("SELECT * FROM transactions WHERE studentUsername = %s", (session['studentUsername'], )) 

    transactions = cur.fetchall()
    cur.execute("select fine from transactions where studentUsername like %s",(session['studentUsername'], ))
    fine=cur.fetchone()
    print ('fine')
    if result > 0:
        return render_template('student_detail.html', transactions = transactions,fine=fine)
    else:
        msg = 'No recorded transactions'
        return render_template('student_detail.html', transactions = transactions,fine= msg)

    # Close connection
    cur.close()

# Logout
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You have logged out.', 'success')
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.secret_key = 'secret123'
    app.run(debug=True)
