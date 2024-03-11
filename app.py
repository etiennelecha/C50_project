import sqlite3
from flask import Flask, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, date



from helpers import admin_page, apology, login_required, student_page

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response



# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# using Python native support of SQL
db = sqlite3.connect('classes.db', check_same_thread = False)
try:
    ADMIN_ID = db.execute("SELECT id FROM users WHERE username LIKE 'admin'").fetchone()[0]
except:
    ADMIN_ID = 0

db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER NOT NULL PRIMARY KEY, username TEXT, first_name TEXT, last_name TEXT, hash TEXT, paid_classes INTEGER)")

db.execute("CREATE TABLE IF NOT EXISTS classes (id INTEGER NOT NULL PRIMARY KEY, class_time UTCDATETIME, max_attendance INTEGER)")

db.execute("CREATE TABLE IF NOT EXISTS bookings (id INTEGER NOT NULL PRIMARY KEY, user_id INTEGER NOT NULL, class_id INTEGER NOT NULL, booking_time DATETIME, class_attended BOOLEAN, FOREIGN KEY (user_id) REFERENCES users(id), FOREIGN KEY (class_id) REFERENCES classes(id))")


@app.route("/", methods=["GET", "POST"])
@login_required
@student_page

def index():

    if request.method == "POST":

        rows = db.execute("SELECT * from bookings WHERE user_id = ? AND class_id = ?", (session["user_id"], int(request.form.get("eventid_to_book")))).fetchall() # check if user already booked to avoid doublons
        
        if len(rows) ==  0:
            db.execute("INSERT INTO bookings (user_id, class_id, booking_time, class_attended) VALUES (?, ?, datetime('now'), 0)", (session["user_id"], int(request.form.get("eventid_to_book"))))
            
            db.execute("COMMIT")
      
    return render_template("index.html", ADMIN_ID = ADMIN_ID)



@app.route("/see_users", methods=["GET", "POST"])
@login_required
@admin_page

def see_users():

    if request.method == "POST":

        paid_classes = db.execute("SELECT paid_classes FROM users WHERE id = ?", (int(request.form.get("user-id")),)).fetchone()[0]
        if not paid_classes:
            paid_classes = 0

        db.execute("UPDATE users SET paid_classes = ? WHERE id = ?", (int(paid_classes) + int(request.form.get("added-classes")), int(request.form.get("user-id"))))
        db.execute("COMMIT")

    return render_template('see_users.html', ADMIN_ID = ADMIN_ID)







@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)
        
        
        
        

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username LIKE ?", (request.form.get("username"),)).fetchall()

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0][4], request.form.get("password")):
            return apology("invalid username and/or password", 403)      

        else:
             # Remember which user has logged in
            session["user_id"] = rows[0][0]               
            # Redirect user to home page
            return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
       
        return render_template("login.html", ADMIN_ID = ADMIN_ID)


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

@app.route('/users_constructor/<class_id>/<user_last_name>', methods=["GET"]) 
@app.route('/users_constructor/<class_id>', methods=["GET"])
@app.route('/users_constructor/GET_ALL/', methods=["GET"])
@app.route('/users_constructor', methods=["GET"])

@login_required

def users_constructor(class_id = 'GET_ALL', user_last_name = ''):

    if class_id == 'GET_ALL':
        isers = db.execute("SELECT * FROM users WHERE last_name LIKE ?", ("%" + user_last_name + "%",)).fetchall()
   
    else:
        isers = db.execute("SELECT * FROM users WHERE id IN (SELECT user_id FROM bookings WHERE class_id = ?)",(int(class_id),)).fetchall()

    users = []

    for at in isers:
        user_attended = db.execute("SELECT COUNT(*) FROM classes WHERE id IN (SELECT class_id FROM bookings WHERE user_id = ? and class_attended = 1)", (int(at[0]),)).fetchone()
        user_booked = db.execute("SELECT COUNT(*) FROM classes WHERE class_time > datetime('now') AND id IN (SELECT class_id FROM bookings WHERE user_id = ?)", (int(at[0]),)).fetchone()      
        at = at + ((user_attended[0] + user_booked[0]),)
        users.append(at)

    users_list = []

    if len(users) != 0:

        for at in users:
            users_dict = {}
            users_dict['id'] = at[0]
            users_dict['username'] = at[1]
            users_dict['first_name'] = at[2]
            users_dict['last_name'] = at[3]
            if not at[5]:
                users_dict['paid_classes'] = 0        
            else:
                users_dict['paid_classes'] = at[5]
            users_dict['attended'] = at[6]
            users_dict['remaining_classes'] = users_dict['paid_classes'] - users_dict['attended']
            if class_id != 'GET_ALL':
                class_attended = db.execute("SELECT class_attended FROM bookings WHERE class_id = ? AND user_id = ?", (int(class_id), at[0])).fetchone()[0]
                users_dict['class_attended'] = class_attended
            users_list.append(users_dict)

    return(jsonify(users_list))







@app.route('/class_constructor/<free_only>/<user_id>/<max_date>/<min_date>/', methods=["GET"]) # free_only either 'YES' or 'NO', user_id to get the bookings of a particular user, dates in YYYY-MM-DD format, the default in SQLite
@app.route('/class_constructor', methods=["GET"])
@app.route('/class_constructor/<free_only>', methods=["GET"])
@app.route('/class_constructor/<free_only>/<user_id>', methods=["GET"])


@login_required

def class_constructor(max_date = '2037-12-31', min_date = '1980-01-01', free_only = 'NO', user_id = 'GET_ALL'):

    if user_id == 'GET_ALL':
        clqsses = db.execute("SELECT * FROM classes WHERE class_time >= ? AND class_time <= ?",(min_date, max_date)).fetchall()  
            
            
    else:
        if user_id == 'current_user':
            us_id = session["user_id"]
        else:
            us_id = user_id
        clqsses = db.execute("SELECT * FROM classes WHERE class_time >= ? AND class_time <= ? AND id IN (SELECT class_id FROM bookings WHERE user_id = ?)" , (min_date, max_date, int(us_id))).fetchall()
    
    classes = []
    for cl in clqsses:
            clqss_date = datetime.strptime(cl[1], "%Y-%m-%d %H:%M:%S")
            if clqss_date > datetime.today(): 
                class_bookings = db.execute("SELECT COUNT(*) FROM users WHERE id IN (SELECT user_id FROM bookings WHERE class_id = ?)", (int(cl[0]),)).fetchone()
            else:
                class_bookings = db.execute("SELECT COUNT(*) FROM users WHERE id IN (SELECT user_id FROM bookings WHERE (class_id = ? AND class_attended = 1))", (int(cl[0]),)).fetchone()
            cl = cl + class_bookings
            classes.append(cl)


    classes_list = []

    if len(classes) != 0:
        

        for cl in classes:
            if free_only == 'YES':
                try:
                    available = (int(cl[2]) - int(cl[3]) > 0)
                    if not available:
                        continue
                except:
                    continue
                year = cl[1][:4]
                month = cl[1][5:-12]
                day = cl[1][8:-9]
                
                
                if date(int(year), int(month), int(day)) < date.today():
                    continue    
            class_dict  = {}            
            class_dict['id'] = cl[0]
            if cl[1][:cl[1].find(' ')] == '' or cl[1][:cl[1].find(' ')] is None:
                class_dict['Date'] = 'Not set'
            else:
                class_dict['Date'] = cl[1][:cl[1].find(' ')]
            if cl[1][cl[1].find(' ') + 1:] == '' or cl[1][cl[1].find(' ') + 1:] is None:
                class_dict['time'] = 'Not set'    
            else:
                class_dict['time'] = cl[1][cl[1].find(' ') + 1:]
            if cl[2] == '' or cl[2] is None:
                class_dict['max_attendance'] = 'Not set'    
            else:
                class_dict['max_attendance'] = cl[2]
            class_dict['bookings'] = cl[3]
            
            classes_list.append(class_dict)
            

    
    return(jsonify(classes_list))



@app.route("/dashboard", methods=["GET", "POST"])
@login_required
@admin_page

def dashboard():

   
    
    if request.method == 'POST':
        if request.form.get('type') == 'A':
        
            if request.form.get('delete-event') == '1':
                db.execute("DELETE FROM classes WHERE id = ?", (int(request.form.get("event-index")),))
            else:
                datetime = request.form.get('event-startDate')
                datetime = datetime[-4:] + '-' + datetime[3:-5] + '-' + datetime[:2]
                if request.form.get('event-time') != '':
                    datetime += ' ' + request.form.get('event-time') + ':00'
                else:
                    datetime += ' 00:00:00'
                if request.form.get('event-index') != '':            
                    db.execute("UPDATE classes SET class_time = ?, max_attendance = ? WHERE id = ?" , (datetime, request.form.get('event-max_attendance'), int(request.form.get('event-index'))))
                    db.execute("COMMIT")
                else:
                
                    db.execute("INSERT INTO classes (class_time, max_attendance) VALUES (?, ?)", (datetime, request.form.get('event-max_attendance')))
                    db.execute("COMMIT")

        if request.form.get('type') == 'B':
            db.execute("UPDATE bookings SET class_attended = 0 WHERE class_id = ?", (int(request.form.get('class-id')),))
            db.execute("COMMIT")
            attendees_id = request.form.get('attendees')
            if attendees_id:

                for attendee_id in attendees_id:
                    db.execute("UPDATE bookings SET class_attended = 1 WHERE (user_id = ? AND class_id = ?)", (int(attendee_id), int(request.form.get('class-id'))))
                    db.execute("COMMIT")
           


    
    
    

    return render_template('dashboard.html', ADMIN_ID = ADMIN_ID)
  






@app.route("/register", methods=["GET", "POST"])
def register():
    
   
    if request.method == "POST":

        # Ensure first AND last name were submitted
        if not request.form.get("first-name"):
            return apology("must provide first name", 400)
        
        elif not request.form.get("last-name"):
            return apology("must provide last name", 400)

        # Ensure username was submitted
        elif not request.form.get("username"):
            return apology("must provide username", 400)

        elif len(db.execute("SELECT * FROM users WHERE username LIKE ?", (request.form.get("username"),)).fetchall()) != 0:
            return apology("username already exists", 400)
        
      

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        elif not request.form.get("confirmation"):
            return apology("must provide password confirmation", 400)

        elif not request.form.get("confirmation") == request.form.get("password"):
            return apology("passwords do not match", 400)

        db.execute("INSERT INTO users (username, hash, first_name, last_name) VALUES (?,?,?,?)", (request.form.get("username"), generate_password_hash(request.form.get("password")), request.form.get("first-name"), request.form.get("last-name")))
        db.execute("COMMIT")

        
        session["user_id"] = db.execute("SELECT id FROM users WHERE username LIKE ?", (request.form.get("username"),)).fetchone()[0]
        
        if request.form.get("username").upper() == 'ADMIN':
            global ADMIN_ID
            ADMIN_ID = session["user_id"]

        return redirect("/")

    else:

        return render_template("register.html", ADMIN_ID = ADMIN_ID)







def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
