from flask import redirect, session
from functools import wraps
import os

def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/latest/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function

def allowed_file(filename, ALLOWED_EXTENSIONS):
    t = filename.split('.')[-1].lower()
    print(t)
    if t in ALLOWED_EXTENSIONS:
        return True
    return False