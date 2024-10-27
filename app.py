import os
import sqlite3
from flask import Flask, flash, redirect, render_template, request, session, g, url_for
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
import random
from time import time as nowtime

import video_helper
from helpers import login_required, allowed_file
from tomp4 import convert_to_mp4, video_size_save

UPLOAD_FOLDER = 'static/uploads/vid/'
SIZE_ALLOWED = 1 * 1024 * 1024 * 1024
DATABASE = 'danceshare.db'
ALLOWED_EXTENSIONS = [
        '.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm',
        '.m4v', '.3gp', '.ts', '.mts', '.m2ts', '.vob', '.ogv',
        '.mxf', '.mpg', '.mpeg', '.m2v', '.divx', '.f4v', '.rm',
        '.rmvb', '.asf', '.dat'
    ]

# Preverimo ali mapa za nalaganje datotek že obstaja, če ne jo ustvarimo
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Configure application
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create database if it doesn't exist
if not os.path.exists(DATABASE):
    print("Creating database...")
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            hash TEXT NOT NULL,
            size INTEGER
        );
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            filepath TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            image_path TEXT,
            filetype TEXT NOT NULL,
            description TEXT,
            group_id TEXT,
            time INTEGER,
            file_size INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    conn.commit()
    conn.close()

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route("/")
@login_required
def index():
    # conect to db
    con = sqlite3.connect(DATABASE)
    cur = con.cursor()

    # get videos from user
    cur.execute("SELECT filepath, name, description FROM videos WHERE user_id = :user_id",{"user_id": session["user_id"]})
    videos = cur.fetchall()
    num_videos = len(videos)

    return render_template("index.html", username=session["user_id"] , num_videos=num_videos, videos=videos)

@app.route("/delete_account", methods=["GET", "POST"])
@login_required
def delete_account():
    print("TODO TODO")

@app.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    return redirect("/")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    # Forget any user_id
    session.clear()

    # conect to db
    con = sqlite3.connect(DATABASE)
    cur = con.cursor()


    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return render_template("login.html", error="must provide username"), 403

        # Ensure password was submitted
        elif not request.form.get("password"):
            return render_template("login.html", error="must provide password"), 403

        # Query database for username
        cur.execute("SELECT * FROM users WHERE username = :username",{"username": request.form.get("username")})
        rows = cur.fetchall()

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0][2], request.form.get("password")):
            return render_template("login.html", error="invalid username and/or password"), 403

        # Remember which user has logged in
        session["user_id"] = rows[0][0]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # conect to db
        con = sqlite3.connect(DATABASE)
        cur = con.cursor()

        # check if form is fealed
        if request.form.get("username") == "" or request.form.get("password") == "":
            return render_template("register.html", error="Form not fealed"), 400

        # get username and password and check if passwords are the same
        if request.form.get("password") == request.form.get("confirmation"):
            username = request.form.get("username")
            password = request.form.get("password")
        else:
            return render_template("register.html", error="password dosn't match"), 400
        
        # check if username is in db
        cur.execute("SELECT * FROM users WHERE username = ?", (username,))
        if cur.fetchone():
            return render_template("register.html", error="username is taken"), 400
        
        # Save user in db
        hash = generate_password_hash(password)
        cur.execute("INSERT INTO users (username, hash, size) VALUES (?, ?, 0);", (username, hash))
        con.commit()

        # Get the id of the user from the database
        cur.execute("SELECT id FROM users WHERE username = ?", (username,))
        session["user_id"] = cur.fetchone()[0]
        con.close()
        return redirect("/")
    else:
        return render_template("register.html")

@app.route("/upload", methods=["GET", "POST"])
@login_required
def uploade():
    if request.method == "POST":
        file = request.files['video']
        group = request.form.get("group")
        name = request.form.get("name")
        description = request.form.get("description")

        # Check if file was uploaded
        if not file:
            print("No file was uploaded.")
            return render_template("uploade.html", error="No file was uploaded."), 400
        
        # Check if file type is allowed
        if allowed_file(file.filename, ALLOWED_EXTENSIONS):
            print("File type not allowed.")
            return render_template("uploade.html", error="File type not allowed."), 400

        # conect to db
        con = sqlite3.connect(DATABASE)
        cur = con.cursor()
        
        # check next available id
        cur.execute("SELECT MAX(id) FROM videos")
        id_temp = cur.fetchone()
        if id_temp[0] is not None:
            id = id_temp[0] + 1
        else:
            id = 1
        

        # rename file to avoid overwriting existing files (in temp folder)
        file.filename = f"{session['user_id']}_{random.randint(1, 9999)}_{round(nowtime()*1000000)}.{file.filename.split('.')[-1].lower()}"

        # Convert to mp4 and get file size
        filetype = file.filename.split('.')[-1].lower()
        if filetype != 'mp4':
            print("Converting to mp4")
            temp = convert_to_mp4(file)
            converted_file = temp[0]
            file_size = temp[1]
            if converted_file is not None:
                file = converted_file
                print("Converted to mp4")
        else:
            file_size = video_size_save(file)

        file_path = f"{UPLOAD_FOLDER}{id}.mp4"
        image_path = f"{UPLOAD_FOLDER}{id}.jpg"
        print(f"File path: {file_path}")
        
        # check if user reached limit of all videos size
        cur.execute("SELECT SUM(file_size) FROM videos WHERE user_id = :user_id",{"user_id": session["user_id"]})
        t = cur.fetchone()
        size = t[0]
        if size is None:
            size = 0
        if size + file_size > SIZE_ALLOWED:
            error = f"Space limit has been reached {SIZE_ALLOWED / 1024 / 1024 / 1024} GB. <br>You have {SIZE_ALLOWED / 1024 / 1024 / 1024 - size / 1024 / 1024 / 1024} <br>Upgrade your plan or delete some videos"
            print(error)
            return render_template("uploade.html", error=error), 400
        # vrite to user table size
        cur.execute("UPDATE users SET size = :size WHERE id = :user_id",{"size": size + file_size, "user_id": session["user_id"]})
        con.commit()

        if file:
            # create folder if it doesent exist
            if not os.path.exists(UPLOAD_FOLDER):
                os.makedirs(UPLOAD_FOLDER)
            file.save(file_path)
        else:
            return render_template("uploade.html", error="Error 123"), 400

        # Get time from video
        time = video_helper.video_length(file_path)

        # Create picture
        video_helper.extract_frame_at(file_path)

        # Video size
        file_size = video_helper.video_size(file_path)
        print(f"File size: {file_size}")

        cur.execute("INSERT INTO `videos` (`name`, `filepath`, `user_id`, `filetype`, `description`, `group_id`, `time`, `image_path`, `file_size`) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
                    , (name, file_path, session["user_id"], filetype, description, group, time, image_path, file_size))
        con.commit()


        return render_template("uploade.html", massage="Video uploaded successfully")
    else:
        return render_template("uploade.html")

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404
app.run(debug=True, host="0.0.0.0", port=8000)