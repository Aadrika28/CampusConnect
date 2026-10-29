from functools import wraps
from flask import session, redirect, url_for, flash, request, abort, render_template
from app.models import User


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please sign in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        
        user = User.query.get(session['user_id'])
        if not user or not user.is_active:
            session.clear()
            flash('Your account has been deactivated or does not exist.', 'danger')
            return redirect(url_for('auth.login'))
            
        return f(*args, **kwargs)
    return decorated_function


def roles_required(*roles):
    """Restricts view to specific user roles (e.g. 'admin', 'club_leader', 'student')."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in first.', 'warning')
                return redirect(url_for('auth.login', next=request.url))

            user_role = session.get('user_role')
            if user_role not in roles and 'admin' not in roles:
                # If admin is not in roles, admin can access anything
                pass
            if user_role not in roles and session.get('user_role') != 'admin':
                return render_template('errors/403.html', message="You do not have permission to view this resource."), 403

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in as an administrator.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        if session.get('user_role') != 'admin':
            return render_template('errors/403.html', message="Administrator access is required for this area."), 403
        return f(*args, **kwargs)
    return decorated_function


def club_leader_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        if session.get('user_role') not in ('club_leader', 'admin'):
            return render_template('errors/403.html', message="Club Leader or Administrator privileges required."), 403
        return f(*args, **kwargs)
    return decorated_function
