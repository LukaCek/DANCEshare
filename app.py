import os
import sqlite3
from flask import Flask, flash, redirect, render_template, request, session, g, url_for,  jsonify, make_response
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
import random
from time import time as nowtime
from io import BytesIO
from werkzeug.datastructures import FileStorage
import traceback

import video_helper
from helpers import login_required, allowed_file
from tomp4 import convert_to_mp4, video_size_save

UPLOAD_FOLDER = 'static/uploads/vid/'
SIZE_ALLOWED = 2 * 1024 * 1024 * 1024
DATABASE = 'data/danceshare.db'
ALLOWED_EXTENSIONS = [
        'mp4', 'mov', 'avi', 'mkv', 'wmv', 'flv', 'webm',
        'm4v', '3gp', 'ts', 'mts', 'm2ts', 'vob', 'ogv',
        'mxf', 'mpg', 'mpeg', 'm2v', 'divx', 'f4v', 'rm',
        'rmvb', 'asf', 'dat', 'wmv', 'mpg'
    ]

# Preverimo ali mapa za nalaganje datotek že obstaja, če ne jo ustvarimo
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Configure application
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['TEMP_FOLDER'] = 'static/uploads/tmp/'

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
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            creator_id INTEGER NOT NULL,
            created_at INTEGER NOT NULL DEFAULT CURRENT_TIMESTAMP,
            public BOOLEAN NOT NULL DEFAULT FALSE,
            hash TEXT DEFAULT NULL,
            FOREIGN KEY (creator_id) REFERENCES users (id)
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS group_members (
            group_id INTEGER,
            user_id INTEGER,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            role TEXT DEFAULT "member",
            PRIMARY KEY (group_id, user_id),
            FOREIGN KEY (group_id) REFERENCES groups (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
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
            group_id INTEGER,
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

@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    # conect to db
    con = sqlite3.connect(DATABASE)
    cur = con.cursor()

    # get videos from user
    cur.execute("SELECT filepath, name, description FROM videos WHERE user_id = :user_id",{"user_id": session["user_id"]})
    videos = cur.fetchall()
    num_videos = len(videos)

    # get groups
    # get groups from user
    cur.execute("""
        SELECT g.id, g.name 
        FROM group_members gm 
        JOIN groups g ON gm.group_id = g.id 
        WHERE gm.user_id = ?
    """, (session["user_id"],))
    groups = cur.fetchall()
    con.close()

    return render_template("index.html", username=session["user_id"] , num_videos=num_videos, videos=videos, groups=groups)

@app.route("/search", methods=["GET"])
@login_required
def search():
    q = request.args.get("q")
    group = request.args.get("group")
    # conect to db
    con = sqlite3.connect(DATABASE)
    cur = con.cursor()
    # gets groups in vitch is user
    cur.execute("""
        SELECT g.id 
        FROM group_members gm 
        JOIN groups g ON gm.group_id = g.id 
        WHERE gm.user_id = ?
    """, (session["user_id"],))
    groupsUserIsIn = cur.fetchall()
    # get videos from user
    if group == "All":
        videos = []
        for g in groupsUserIsIn:
            cur.execute("SELECT filepath, videos.name, videos.id, groups.name FROM videos JOIN groups ON videos.group_id = groups.id WHERE videos.group_id = :group AND videos.name LIKE :q" ,{"group": g[0], "q": f"%{q}%"})
            videos += cur.fetchall()
            print(f"videos: {videos}")
    else:
        cur.execute("SELECT filepath, videos.name, videos.id, groups.name FROM videos JOIN groups ON videos.group_id = groups.id WHERE videos.group_id = :group AND videos.name LIKE :q AND videos.group_id = :group" ,{"group": group, "q": f"%{q}%", "group": group})
        videos = cur.fetchall()

    # get groups
    # get groups from user
    cur.execute("""
        SELECT g.id, g.name
        FROM group_members gm 
        JOIN groups g ON gm.group_id = g.id 
        WHERE gm.user_id = ?
    """, (session["user_id"],))
    groups = cur.fetchall()
    con.close()
    
    return render_template("search.html", videos=videos)

@app.route("/delete_account/<int:user_id>", methods=["POST", "GET"])
@login_required
def delete_account(user_id):
    if session["user_id"] == user_id:
        # conect to db
        con = sqlite3.connect(DATABASE)
        cur = con.cursor()

        # get if of all videos to delete
        cur.execute("SELECT `id` FROM `videos` WHERE `user_id` = ?", (user_id,))
        videos = cur.fetchall()

        # loop through videos and delete
        for video in videos:
            cur.execute("SELECT filepath, image_path FROM videos WHERE id = ?", (video[0],))
            path = cur.fetchone()
            result = video_helper.deleteVideoAndPicture(path[0], path[1])
            # delete video from db
            if result == True:
                cur.execute("DELETE FROM `videos` WHERE `id` = ?", (video[0],))

        # delete user
        cur.execute("DELETE FROM users WHERE id = :user_id",{"user_id": user_id})
        cur.execute("DELETE FROM group_members WHERE user_id = :user_id",{"user_id": user_id})
        con.commit()
        con.close()
        session.clear()
        return redirect("/")
    else:
        return "You are not the owner of this account", 401

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
        end = False
        try:
            print("Received upload request")
            print("Form data:", request.form)
            print("Files:", request.files)

            if 'file' not in request.files:
                return make_response(jsonify({'error': 'No file part'}), 400)
            
            file = request.files['file']
            print("File received:", file.filename)
            
            # Get form data with error handling
            try:
                chunk_number = int(request.form.get('chunk_number', '0'))
                total_chunks = int(request.form.get('total_chunks', '0'))
                file_type = request.form.get('file_type', '')
                video_name = request.form.get('video_name', '')
                description = request.form.get('description', '')
                group = request.form.get('group', '')
                
                # Get file extension from MIME type
                extension = ''
                if '/' in file_type:
                    extension = '.' + file_type.split('/')[-1]
                
                filename = f"{session['user_id']}_{video_name}{extension}"
            except ValueError as e:
                print("Error parsing form data:", str(e))
                return make_response(jsonify({'error': 'Invalid form data'}), 400)
            
            print(f"Processing chunk {chunk_number + 1} of {total_chunks} for file {filename}")
            
            # Create a temporary folder for chunks
            temp_folder = os.path.join(app.config['TEMP_FOLDER'], filename)
            if not os.path.exists(temp_folder):
                os.makedirs(temp_folder)
            
            # Save the chunk
            chunk_path = os.path.join(temp_folder, f'chunk_{chunk_number}')
            print(f"Saving chunk to: {chunk_path}")
            file.save(chunk_path)
            
            # If this is the last chunk, combine all chunks
            if chunk_number == total_chunks - 1:
                print("Processing final chunk, combining files...")
                
                try:
                    # Create BytesIO object to store file in memory
                    file_stream = BytesIO()
                    
                    # Combine all chunks into memory
                    for i in range(total_chunks):
                        chunk_file = os.path.join(temp_folder, f'chunk_{i}')
                        if os.path.exists(chunk_file):
                            with open(chunk_file, 'rb') as infile:
                                file_stream.write(infile.read())
                        else:
                            raise Exception(f'Missing chunk {i}')
                    
                    # Reset stream position to start
                    file_stream.seek(0)
                    
                    # Create FileStorage object
                    file = FileStorage(
                        stream=file_stream,
                        filename=filename,
                        content_type=file_type
                    )
                    
                    # Save to disk (optional, you can remove this if you don't need it)
                    #final_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    #final_file.save(final_path)
                    
                    # Prints all received metadata
                    print(" Metadata" * 5 + ":")
                    print(f'Name: {video_name}')
                    print(f'Description: {description}')
                    print(f'File Type: {file_type}')
                    print(f'Group: {group}')
                    print(f'FileStorage object created with size: {file_stream.tell()} bytes')
                    
                    # Clean up chunks
                    for i in range(total_chunks):
                        try:
                            chunk_file = os.path.join(temp_folder, f'chunk_{i}')
                            if os.path.exists(chunk_file):
                                os.remove(chunk_file)
                        except Exception as e:
                            print(f"Error removing chunk {i}: {str(e)}")
                    
                    try:
                        if os.path.exists(temp_folder):
                            os.rmdir(temp_folder)
                    except Exception as e:
                        print(f"Error removing temp folder: {str(e)}")
                    
                    print(f"File reconstruction complete")
                    # Do something with the final file ### END ###
                    end = True
                
                except Exception as e:
                    print(f"Error during file reconstruction: {str(e)}")
                    traceback.print_exc()
                    return make_response(jsonify({'error': f'File reconstruction failed: {str(e)}'}), 500)
            
            if end != True:
                response = make_response(jsonify({'message': f'Chunk {chunk_number + 1} of {total_chunks} received'}))
                return response, 200
            
        except Exception as e:
            print("Error during upload:")
            print(str(e))
            traceback.print_exc()
            response = make_response(jsonify({'error': str(e)}))
            return response, 500
#       file = request.files['video']
#       group = request.form.get("group")
#       name = request.form.get("name")
#       description = request.form.get("description")

        # Check if file was uploaded
        if not file:
            print("No file was uploaded.")
            return make_response(jsonify({'error': "No file was uploaded."})), 400
        
        # Check if group is selected
        if group is None:
            print("No group was selected.")
            return make_response(jsonify({'error': "No group was selected."})), 400
        
        # Check if file type is allowed
        if allowed_file(file.filename, ALLOWED_EXTENSIONS):
            print("File type not allowed.")
            return make_response(jsonify({'error': "File type not allowed."})), 400

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
        
        # get file type
        filetype = file.filename.split('.')[-1].lower()
        

        # check if file is mp4 widouth modification
        if filetype != 'mp4':
            print("Converting to mp4")
            temp = convert_to_mp4(file)
            if temp is None:
                return make_response(jsonify({'error': "File conversion failed."})), 400
            converted_file = temp[0]
            file_size = temp[1]
            print(f"Converted file: {converted_file}")
            print(f"File size: {file_size}")
            if converted_file is not None:
                file = converted_file
                print("Converted to mp4")
        else:
            # extract file size
            f = video_size_save(file)
            file_size = f[1]
            file = f[0]

            if file_size is None:
                return make_response(jsonify({'error': "Failed to get video size(mp4)."})), 400

        file_path = os.path.join(UPLOAD_FOLDER, f"{id}.mp4")
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
            return make_response(jsonify({'error': f"{error}"})), 400
        # write to user table size
        cur.execute("UPDATE users SET size = :size WHERE id = :user_id",{"size": size + file_size, "user_id": session["user_id"]})
        con.commit()

        if file:
            # create folder if it doesent exist
            if not os.path.exists(UPLOAD_FOLDER):
                os.makedirs(UPLOAD_FOLDER)
            file.save(file_path)
        else:
            return make_response(jsonify({'error': "Error 123"})), 400

        # Get time from video
        time = video_helper.video_length(file_path)

        # Create picture
        video_helper.extract_frame_at(file_path)

        # Video size
        file_size = video_helper.video_size(file_path)
        print(f"File size: {file_size}")

        cur.execute("INSERT INTO `videos` (`name`, `filepath`, `user_id`, `filetype`, `description`, `group_id`, `time`, `image_path`, `file_size`) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
                    , (video_name, file_path, session["user_id"], filetype, description, group, time, image_path, file_size))
        con.commit()

        return make_response(jsonify({'error': "Video uploaded successfully"})), 200
    else:
        # conect to db
        con = sqlite3.connect(DATABASE)
        cur = con.cursor()
        # get groups
        # get groups from user
        cur.execute("""
            SELECT g.id, g.name 
            FROM group_members gm 
            JOIN groups g ON gm.group_id = g.id 
            WHERE gm.user_id = ?
        """, (session["user_id"],))
        groups = cur.fetchall()
        con.close()

        return render_template("uploade.html", groups=groups)

@app.route("/options", methods=["GET"])
@login_required
def options():
    con = sqlite3.connect(DATABASE)
    cur = con.cursor()
    cur.execute("SELECT username FROM users WHERE id = ?", (session["user_id"],))
    username = cur.fetchone()[0]
    con.close()
    return render_template("options.html", user_id=session["user_id"], username=username)

@app.route("/create-group", methods=["GET", "POST"])
@login_required
def create_group():
    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")
        public = request.form.get("public")
        password = request.form.get("password")

        # check if form is fealed
        if name == "" or description == "" or public == "":
            return render_template("create-group.html", error="Form not fealed!"), 400
        
        # reformat public
        if public == "on":
            public = True
        else:
            public = False
        
        # check if password is fealed
        if password == "" or password is None:
            hash = None
        else:
            hash = generate_password_hash(password)

        # conect to db
        con = sqlite3.connect(DATABASE)
        cur = con.cursor()

        # check if group exists
        cur.execute("SELECT * FROM `groups` WHERE `name` = ?", (name,))
        result = cur.fetchone()

        # if group exists
        if result is not None:
            con.close() # close db
            return render_template("create-group.html", error="Group name already exists!"), 400

        # create group
        cur.execute("INSERT INTO `groups` (`name`, `description`, 'creator_id', 'public', 'hash') VALUES (?, ?, ?, ?, ?)", (name, description, session["user_id"], public, hash))
        con.commit()

        # get id of created group
        cur.execute("SELECT last_insert_rowid()")
        group_id = cur.fetchone()[0]

        con.close() # close db
        return redirect(f"/group/{group_id}/join")
    else:
        return render_template("create-group.html")

@app.route("/video/<video_id>/edit", methods=["GET", "POST"])
@login_required
def edit_video(video_id):
    if request.method == "GET":
        # conect to db
        con = sqlite3.connect(DATABASE)
        cur = con.cursor()

        # check if video exists
        cur.execute("SELECT * FROM videos WHERE id = ?", (video_id,))
        video = cur.fetchone()
        if video is None:
            con.close()
            return "Video does not exist! Go <a href='/'>home</a>.", 404
        
        user_is_allowed_to_edit = False
        # check if user is allowed to edit video
        # check if user is owner of video
        cur.execute("SELECT user_id FROM videos WHERE id = ?", (video_id,))
        video_user_id = cur.fetchone()[0]
        if video_user_id == session["user_id"]:
            user_is_allowed_to_edit = True

        # check if user is creator of group in which video is
        cur.execute("SELECT creator_id FROM groups WHERE id = (SELECT group_id FROM videos WHERE id = ?)", (video_id,))
        group_user_id = cur.fetchone()[0]
        if group_user_id == session["user_id"]:
            user_is_allowed_to_edit = True

        if not user_is_allowed_to_edit:
            con.close()
            return "You are not allowed to edit this video! Go <a href='/'>home</a>.", 403
        
        # get video data
        cur.execute("SELECT name, filepath, description, time, file_size FROM videos WHERE id = ?", (video_id,))
        video = cur.fetchone()

        con.close()
        return render_template("edit-video.html", video_id=video_id, video=video)
    else:
        name = request.form.get("name")
        description = request.form.get("description")

        # conect to db
        con = sqlite3.connect(DATABASE)
        cur = con.cursor()

        user_is_allowed_to_edit = False
        # check if user is allowed to edit video
        # check if user is owner of video
        cur.execute("SELECT user_id FROM videos WHERE id = ?", (video_id,))
        video_user_id = cur.fetchone()[0]
        if video_user_id == session["user_id"]:
            user_is_allowed_to_edit = True

        # check if user is creator of group in which video is
        cur.execute("SELECT creator_id FROM groups WHERE id = (SELECT group_id FROM videos WHERE id = ?)", (video_id,))
        group_user_id = cur.fetchone()[0]
        if group_user_id == session["user_id"]:
            user_is_allowed_to_edit = True

        if not user_is_allowed_to_edit:
            con.close()
            return "You are not allowed to edit this video! Go <a href='/'>home</a>.", 40

        # update video
        cur.execute("UPDATE `videos` SET `name` = ?, `description` = ? WHERE `id` = ?", (name, description, video_id))
        con.commit()

        con.close() # close db
        return redirect(f"/")


@app.route("/video/<video_id>/delete", methods=["POST"])
@login_required
def delete_video(video_id):
    # conect to db
    con = sqlite3.connect(DATABASE)
    cur = con.cursor()

    user_is_allowed_to_edit = False
    # check if user is allowed to edit video
    # check if user is owner of video
    cur.execute("SELECT user_id FROM videos WHERE id = ?", (video_id,))
    video_user_id = cur.fetchone()[0]
    if video_user_id == session["user_id"]:
        user_is_allowed_to_edit = True

    # check if user is creator of group in which video is
    cur.execute("SELECT creator_id FROM groups WHERE id = (SELECT group_id FROM videos WHERE id = ?)", (video_id,))
    group_user_id = cur.fetchone()[0]
    if group_user_id == session["user_id"]:
        user_is_allowed_to_edit = True

    if not user_is_allowed_to_edit:
        con.close()
        return "You are not allowed to edit this video! Go <a href='/'>home</a>.", 40
    
    # delit video
    cur.execute("DELETE FROM `videos` WHERE `id` = ?", (video_id,))
    con.commit()

    con.close() # close db
    return redirect(f"/")

@app.route("/group/<group_id>/edit", methods=["GET", "POST"])
@login_required
def edit_group(group_id):
    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")
        password = request.form.get("password")
        public = request.form.get("public")

        # check if form is fealed
        if name == "" or description == "" or public == "":
            return render_template("edit-group.html", error="Form not fealed!"), 400
        
        # reformat public
        if public == "on":
            public = True
        else:
            public = False

        # conect to db
        con = sqlite3.connect(DATABASE)
        cur = con.cursor()

        # check if password is fealed
        if password == "" or password is None:
            '''don't change hash'''
            # update group
            cur.execute("UPDATE `groups` SET `name` = ?, `description` = ?, `public` = ? WHERE `id` = ?", (name, description, public, group_id))
            con.commit()
        else:
            hash = generate_password_hash(password)
            # update group
            cur.execute("UPDATE `groups` SET `name` = ?, `description` = ?, `public` = ?, `hash` = ? WHERE `id` = ?", (name, description, public, hash, group_id))
            con.commit()

        con.close() # close db
        return redirect(f"/browse-groups")
    else:
        # conect to db
        con = sqlite3.connect(DATABASE)
        cur = con.cursor()

        # check if user is creator of group
        cur.execute("SELECT creator_id FROM `groups` WHERE `id` = ?", (group_id,))
        result = cur.fetchone()[0]
        # if user is not creator of group
        if result != session["user_id"]:
            con.close() # close db
            return render_template("edit-group.html", error="You are not the creator of this group!"), 400

        # get group info
        cur.execute("SELECT name, description, public FROM groups WHERE `id` = ?", (group_id, ))
        result = cur.fetchone()

        con.close() # close db
        return render_template("edit-group.html", group_id=group_id, name=result[0], description=result[1], public=result[2])

@app.route("/browse-groups", methods=["GET"])
@login_required
def browse_groups():
    return render_template("browse-groups.html")

@app.route("/browse-groups-api", methods=["GET"])
@login_required
def browse_groups_api():
    q = request.args.get("q")
    '''list of public groups and groups user is in'''
    # conect to db
    con = sqlite3.connect(DATABASE)
    cur = con.cursor()

    # get groups with membership status for current user
    # Using LEFT JOIN to show all groups, even if user isn't a member
    cur.execute("""
        SELECT 
            g.id, g.name, g.description, g.public, g.creator_id,
            CASE 
                WHEN gm.user_id IS NOT NULL THEN 1 
                ELSE 0 
            END as is_member
        FROM groups g
        LEFT JOIN group_members gm ON g.id = gm.group_id 
            AND gm.user_id = ?
        WHERE g.name LIKE ? OR g.description LIKE ?
        ORDER BY is_member DESC
    """, (session["user_id"], f"%{q}%", f"%{q}%"))
    groups = cur.fetchall()

    # close db
    con.close()
    return render_template("browse-groups-api.html", groups=groups, user_id=session["user_id"], q=q)

@app.route("/group/<int:group_id>/join")
@login_required
def group(group_id):
    # conect to db
    con = sqlite3.connect(DATABASE)
    cur = con.cursor()

    # check if user is already in group
    cur.execute("SELECT * FROM `group_members` WHERE `group_id` = ? AND `user_id` = ?", (group_id, session["user_id"]))
    result = cur.fetchone()

    # if user is already in group
    if result is not None:
        con.close() # close db
        return render_template("browse-groups.html", error="You are already in this group! Or group does not exist"), 400

    # check if group is password protected
    cur.execute("SELECT `hash` FROM `groups` WHERE `id` = ?", (group_id,))
    hash = cur.fetchone()[0]
    if hash is not None:
        con.close() # close db
        return redirect("/group/" + str(group_id) + "/join/password")

    # add user to group
    cur.execute("INSERT INTO `group_members` (`group_id`, `user_id`) VALUES (?, ?)", (group_id, session["user_id"]))
    con.commit()

    # close db
    con.close()
    return redirect("/browse-groups")

@app.route("/group/<int:group_id>/join/password", methods=["GET", "POST"])
@login_required
def group_password(group_id):
    if request.method == "POST":
        password = request.form.get("password")

        # check if password is correct
        con = sqlite3.connect(DATABASE)
        cur = con.cursor()
        cur.execute("SELECT `hash` FROM `groups` WHERE `id` = ?", (group_id,))
        hash = cur.fetchone()[0]
        if hash is None:
            con.close() # close db
            return render_template("group-password.html", error="Group is not password protected!"), 400
        if check_password_hash(hash, password):
            cur.execute("INSERT INTO `group_members` (`group_id`, `user_id`) VALUES (?, ?)", (group_id, session["user_id"]))
            con.commit()
            con.close() # close db
            return redirect("/browse-groups")
        else:
            con.close() # close db
            return render_template("group-password.html", error="Incorrect password!"), 400
    else:
        return render_template("group-password.html", group_id=group_id)

@app.route("/group/<int:group_id>/leave", methods=["GET"])
@login_required
def leave_group(group_id):
    # conect to db
    con = sqlite3.connect(DATABASE)
    cur = con.cursor()

    # remove user from group
    cur.execute("DELETE FROM `group_members` WHERE `group_id` = ? AND `user_id` = ?", (group_id, session["user_id"]))
    con.commit()

    # close db
    con.close()
    return redirect("/browse-groups")

@app.route("/group/<int:group_id>/delete", methods=["POST"])
@login_required
def delete_group(group_id):
    # conect to db
    con = sqlite3.connect(DATABASE)
    cur = con.cursor()

    # delete all videos and pictures in group
    # get if of all videos to delete
    cur.execute("SELECT `id` FROM `videos` WHERE `group_id` = ?", (group_id,))
    videos = cur.fetchall()

    # loop through videos and delete
    for video in videos:
        cur.execute("SELECT filepath, image_path FROM videos WHERE id = ?", (video[0],))
        path = cur.fetchone()
        result = video_helper.deleteVideoAndPicture(path[0], path[1])
        # delete video from db
        if result == True:
            cur.execute("DELETE FROM `videos` WHERE `id` = ?", (video[0],))
            con.commit()
    
    # delete group
    cur.execute("DELETE FROM `groups` WHERE `id` = ?", (group_id,))
    cur.execute("DELETE FROM `group_members` WHERE `group_id` = ?", (group_id,))
    con.commit()

    # close db
    con.close()
    return redirect("/browse-groups")

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

app.run(host="0.0.0.0", port=8080)