from functools import wraps
from flask import redirect, url_for, session

def login_required(min_level=1):
    def d(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if 'username' not in session: return redirect(url_for('auth.login'))
            if session.get('level',0) < min_level: return "权限不足", 403
            return f(*args, **kwargs)
        return wrapped
    return d