import re
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
from app.models import db, User, Club, Event, EventRegistration, Attendance, Announcement, AuditLog
from app.decorators import login_required, admin_required
from app.utils.audit import log_audit

admin_bp = Blueprint('admin', __name__)


def slugify(text):
    text = re.sub(r'[^\w\s-]', '', text.lower())
    return re.sub(r'[-\s]+', '-', text).strip('-')


@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """Administrator Overview Dashboard with platform-wide health metrics."""
    total_students = User.query.filter_by(role='student').count()
    total_leaders = User.query.filter_by(role='club_leader').count()
    total_admins = User.query.filter_by(role='admin').count()
    total_users = User.query.count()

    total_clubs = Club.query.count()
    active_clubs = Club.query.filter_by(is_active=True).count()

    total_events = Event.query.count()
    upcoming_events = Event.query.filter(Event.event_date >= datetime.utcnow(), Event.status == 'published').count()

    total_registrations = EventRegistration.query.filter_by(status='confirmed').count()
    total_attendance = Attendance.query.count()
    attendance_rate = round((total_attendance / total_registrations * 100), 1) if total_registrations > 0 else 0

    # Recent Audit Logs
    recent_logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(8).all()

    # Recent Platform Registrations
    recent_registrations = EventRegistration.query.order_by(EventRegistration.registered_at.desc()).limit(6).all()

    return render_template(
        'admin/dashboard.html',
        total_students=total_students,
        total_leaders=total_leaders,
        total_admins=total_admins,
        total_users=total_users,
        total_clubs=total_clubs,
        active_clubs=active_clubs,
        total_events=total_events,
        upcoming_events=upcoming_events,
        total_registrations=total_registrations,
        total_attendance=total_attendance,
        attendance_rate=attendance_rate,
        recent_logs=recent_logs,
        recent_registrations=recent_registrations
    )


@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """Searchable & filterable user management table."""
    search_query = request.args.get('q', '').strip()
    role_filter = request.args.get('role', 'all')
    status_filter = request.args.get('status', 'all')

    query = User.query

    if role_filter != 'all':
        query = query.filter_by(role=role_filter)

    if status_filter == 'active':
        query = query.filter_by(is_active=True)
    elif status_filter == 'inactive':
        query = query.filter_by(is_active=False)

    if search_query:
        query = query.filter(
            db.or_(
                User.name.ilike(f"%{search_query}%"),
                User.email.ilike(f"%{search_query}%"),
                User.student_id.ilike(f"%{search_query}%"),
                User.department.ilike(f"%{search_query}%")
            )
        )

    users_list = query.order_by(User.created_at.desc()).all()
    active_admins_count = User.query.filter_by(role='admin', is_active=True).count()

    return render_template(
        'admin/users.html',
        users=users_list,
        search_query=search_query,
        role_filter=role_filter,
        status_filter=status_filter,
        active_admins_count=active_admins_count
    )


@admin_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_user_status(user_id):
    """Safely activate or deactivate user accounts, protecting the last admin."""
    user = User.query.get_or_404(user_id)
    current_admin_id = session['user_id']

    # Prevent deactivating the last active administrator
    if user.role == 'admin' and user.is_active:
        active_admins = User.query.filter_by(role='admin', is_active=True).count()
        if active_admins <= 1:
            flash('Safety check triggered: Cannot deactivate the last active administrator on the platform.', 'danger')
            return redirect(url_for('admin.users'))

    user.is_active = not user.is_active
    db.session.commit()

    action = 'ACTIVATED' if user.is_active else 'DEACTIVATED'
    log_audit(f'USER_{action}', 'User', user.id, f"Admin {session.get('user_name')} set user {user.name} active={user.is_active}")
    flash(f'User "{user.name}" has been {action.lower()}.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/change-role', methods=['POST'])
@login_required
@admin_required
def change_user_role(user_id):
    """Safely change user roles with lockout protection."""
    user = User.query.get_or_404(user_id)
    new_role = request.form.get('role')

    if new_role not in ('student', 'club_leader', 'admin'):
        flash('Invalid role specified.', 'danger')
        return redirect(url_for('admin.users'))

    # If demoting an admin, ensure at least one other active admin remains
    if user.role == 'admin' and new_role != 'admin':
        active_admins = User.query.filter_by(role='admin', is_active=True).count()
        if active_admins <= 1:
            flash('Safety check triggered: Cannot demote the last administrator. Platform must have at least one active admin.', 'danger')
            return redirect(url_for('admin.users'))

    old_role = user.role
    user.role = new_role
    db.session.commit()

    log_audit('ROLE_CHANGE', 'User', user.id, f"Changed role of {user.name} from {old_role} to {new_role}")
    flash(f'Role for "{user.name}" updated to {new_role}.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/clubs', methods=['GET', 'POST'])
@login_required
@admin_required
def clubs():
    """Manage campus clubs and create new student societies."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '').strip()
        coordinator = request.form.get('faculty_coordinator', '').strip()
        leader_id = request.form.get('leader_id', type=int)

        if not name or not description or not category or not coordinator:
            flash('All club fields are required.', 'danger')
            return redirect(url_for('admin.clubs'))

        # Check existing club
        if Club.query.filter_by(name=name).first():
            flash(f'A club named "{name}" already exists.', 'danger')
            return redirect(url_for('admin.clubs'))

        base_slug = slugify(name)
        slug = base_slug
        count = 1
        while Club.query.filter_by(slug=slug).first():
            slug = f"{base_slug}-{count}"
            count += 1

        new_club = Club(
            name=name,
            slug=slug,
            description=description,
            category=category,
            faculty_coordinator=coordinator,
            leader_id=leader_id or None,
            is_active=True
        )
        db.session.add(new_club)

        # If leader assigned, ensure their role is club_leader
        if leader_id:
            leader_user = User.query.get(leader_id)
            if leader_user and leader_user.role == 'student':
                leader_user.role = 'club_leader'

        db.session.commit()
        log_audit('CLUB_CREATE', 'Club', new_club.id, f"Created club '{name}'")
        flash(f'Club "{name}" successfully established.', 'success')
        return redirect(url_for('admin.clubs'))

    clubs_list = Club.query.order_by(Club.name.asc()).all()
    potential_leaders = User.query.filter(User.role.in_(['club_leader', 'student']), User.is_active == True).order_by(User.name.asc()).all()
    categories = ['Technical', 'Cultural', 'Sports', 'Literary', 'Social Welfare', 'Entrepreneurship']

    return render_template(
        'admin/clubs.html',
        clubs=clubs_list,
        potential_leaders=potential_leaders,
        categories=categories
    )


@admin_bp.route('/clubs/<int:club_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_club_status(club_id):
    """Toggle club active/inactive status."""
    club = Club.query.get_or_404(club_id)
    club.is_active = not club.is_active
    db.session.commit()

    action = 'Activated' if club.is_active else 'Deactivated'
    log_audit('CLUB_STATUS_CHANGE', 'Club', club.id, f"{action} club {club.name}")
    flash(f'Club "{club.name}" {action.lower()}.', 'info')
    return redirect(url_for('admin.clubs'))


@admin_bp.route('/events')
@login_required
@admin_required
def events():
    """Oversee and moderate all campus events."""
    events_list = Event.query.order_by(Event.event_date.desc()).all()
    return render_template('admin/events.html', events=events_list)


@admin_bp.route('/events/<int:event_id>/status', methods=['POST'])
@login_required
@admin_required
def change_event_status(event_id):
    """Admin moderate event status (published, cancelled, completed, draft)."""
    event = Event.query.get_or_404(event_id)
    new_status = request.form.get('status')

    if new_status in ('draft', 'published', 'cancelled', 'completed'):
        event.status = new_status
        db.session.commit()
        log_audit('EVENT_STATUS_CHANGE', 'Event', event.id, f"Changed event {event.title} status to {new_status}")
        flash(f'Event status updated to {new_status}.', 'success')

    return redirect(url_for('admin.events'))


@admin_bp.route('/announcements', methods=['GET', 'POST'])
@login_required
@admin_required
def announcements():
    """Create and manage platform-wide announcements."""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        priority = request.form.get('priority', 'normal')

        new_ann = Announcement(
            title=title,
            content=content,
            scope='platform',
            author_id=session['user_id'],
            priority=priority
        )
        db.session.add(new_ann)
        db.session.commit()

        log_audit('ANNOUNCEMENT_CREATE', 'Announcement', new_ann.id, f"Platform announcement: '{title}'")
        flash('Platform-wide announcement broadcasted successfully.', 'success')
        return redirect(url_for('admin.announcements'))

    announcements_list = Announcement.query.filter_by(scope='platform').order_by(Announcement.created_at.desc()).all()
    return render_template('admin/announcements.html', announcements=announcements_list)


@admin_bp.route('/announcements/<int:ann_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_announcement(ann_id):
    """Delete an announcement."""
    ann = Announcement.query.get_or_404(ann_id)
    db.session.delete(ann)
    db.session.commit()
    log_audit('ANNOUNCEMENT_DELETE', 'Announcement', ann_id, f"Deleted announcement '{ann.title}'")
    flash('Announcement removed.', 'info')
    return redirect(url_for('admin.announcements'))


@admin_bp.route('/audit-logs')
@login_required
@admin_required
def audit_logs():
    """Security audit trail log viewer."""
    action_filter = request.args.get('action', '').strip()
    query = AuditLog.query

    if action_filter:
        query = query.filter_by(action=action_filter)

    logs = query.order_by(AuditLog.timestamp.desc()).limit(100).all()
    actions = [r[0] for r in db.session.query(AuditLog.action).distinct().all()]

    return render_template('admin/audit_logs.html', logs=logs, actions=actions, selected_action=action_filter)
