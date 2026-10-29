from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g
from app.models import db, User, AuditLog
from app.decorators import login_required
from app.utils.audit import log_audit

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User authentication with role-based dashboard redirection."""
    if 'user_id' in session:
        # Redirect logged-in users to their respective dashboards
        role = session.get('user_role')
        if role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif role == 'club_leader':
            return redirect(url_for('club_leader.dashboard'))
        return redirect(url_for('student.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        if not email or not password:
            flash('Please enter both email address and password.', 'danger')
            return render_template('auth/login.html', email=email)

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash('Invalid email address or password. Please try again.', 'danger')
            return render_template('auth/login.html', email=email)

        if not user.is_active:
            flash('Your account has been deactivated. Please contact campus administration.', 'danger')
            return render_template('auth/login.html', email=email)

        # Set session attributes
        session.clear()
        session['user_id'] = user.id
        session['user_name'] = user.name
        session['user_email'] = user.email
        session['user_role'] = user.role
        session.permanent = remember

        log_audit('USER_LOGIN', 'User', user.id, f"User {user.name} ({user.email}) logged in successfully.", user.id)

        flash(f'Welcome back, {user.name}!', 'success')

        next_url = request.args.get('next')
        if next_url and next_url.startswith('/'):
            return redirect(next_url)

        if user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif user.role == 'club_leader':
            return redirect(url_for('club_leader.dashboard'))
        else:
            return redirect(url_for('student.dashboard'))

    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Student self-registration."""
    if 'user_id' in session:
        return redirect(url_for('student.dashboard'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        student_id = request.form.get('student_id', '').strip().upper()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        department = request.form.get('department', '').strip()
        batch_year = request.form.get('batch_year', type=int) or 2025
        phone = request.form.get('phone', '').strip()

        # Input validations
        errors = []
        if not name or len(name) < 2:
            errors.append("Please provide a valid full name (minimum 2 characters).")
        if not student_id:
            errors.append("Student ID / Roll Number is required.")
        if not email or '@' not in email:
            errors.append("Please provide a valid college or personal email address.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters long.")
        if password != confirm_password:
            errors.append("Passwords do not match.")

        # Check existing email
        if User.query.filter_by(email=email).first():
            errors.append("An account with this email already exists.")

        # Check existing student ID
        if User.query.filter_by(student_id=student_id).first():
            errors.append("A student with this Student ID is already registered.")

        if errors:
            for err in errors:
                flash(err, 'danger')
            return render_template('auth/register.html', form_data=request.form)

        # Create new student account
        user = User(
            name=name,
            student_id=student_id,
            email=email,
            role='student',
            department=department or 'General Studies',
            batch_year=batch_year,
            phone=phone or None,
            is_active=True
        )
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        log_audit('USER_REGISTER', 'User', user.id, f"New student registered: {user.name} ({user.student_id})", user.id)

        flash('Registration successful! You can now log in with your credentials.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


@auth_bp.route('/logout')
def logout():
    """Logout current user and invalidate session."""
    user_id = session.get('user_id')
    user_name = session.get('user_name')
    if user_id:
        log_audit('USER_LOGOUT', 'User', user_id, f"User {user_name} logged out.", user_id)
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """View and update profile information."""
    user = User.query.get_or_404(session['user_id'])

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update_profile':
            user.name = request.form.get('name', '').strip()
            user.department = request.form.get('department', '').strip()
            user.phone = request.form.get('phone', '').strip()
            
            db.session.commit()
            session['user_name'] = user.name
            log_audit('PROFILE_UPDATE', 'User', user.id, "Profile information updated.", user.id)
            flash('Profile details updated successfully.', 'success')

        elif action == 'change_password':
            current_pw = request.form.get('current_password', '')
            new_pw = request.form.get('new_password', '')
            confirm_new_pw = request.form.get('confirm_new_password', '')

            if not user.check_password(current_pw):
                flash('Current password entered is incorrect.', 'danger')
            elif len(new_pw) < 6:
                flash('New password must be at least 6 characters.', 'danger')
            elif new_pw != confirm_new_pw:
                flash('New passwords do not match.', 'danger')
            else:
                user.set_password(new_pw)
                db.session.commit()
                log_audit('PASSWORD_CHANGE', 'User', user.id, "User changed account password.", user.id)
                flash('Password changed successfully.', 'success')

        return redirect(url_for('auth.profile'))

    return render_template('auth/profile.html', user=user)
