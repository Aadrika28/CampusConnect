from datetime import datetime
from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from app.models import db, User, Event, EventRegistration, Club, ClubMembership, Attendance, Announcement, Notification
from app.decorators import login_required

student_bp = Blueprint('student', __name__)


@student_bp.route('/dashboard')
@login_required
def dashboard():
    """Modern Student Dashboard with real-time participation metrics and upcoming activities."""
    user = User.query.get_or_404(session['user_id'])
    now = datetime.utcnow()

    # User's confirmed event registrations
    registrations = EventRegistration.query.filter_by(user_id=user.id, status='confirmed').all()
    reg_event_ids = [r.event_id for r in registrations]

    # Upcoming registered events
    upcoming_registered_events = Event.query.filter(
        Event.id.in_(reg_event_ids) if reg_event_ids else False,
        Event.event_date >= now,
        Event.status == 'published'
    ).order_by(Event.event_date.asc()).limit(4).all()

    # User's joined clubs
    memberships = ClubMembership.query.filter_by(user_id=user.id).all()
    user_club_ids = [m.club_id for m in memberships]
    joined_clubs = Club.query.filter(Club.id.in_(user_club_ids)).all() if user_club_ids else []

    # Recent announcements relevant to student (platform announcements or clubs the student belongs to)
    announcements_query = Announcement.query.filter(
        db.or_(
            Announcement.scope == 'platform',
            db.and_(Announcement.scope == 'club', Announcement.club_id.in_(user_club_ids)) if user_club_ids else False
        )
    ).order_by(Announcement.created_at.desc()).limit(5).all()

    # Discover upcoming events (not registered yet)
    explore_events = Event.query.filter(
        Event.id.notin_(reg_event_ids) if reg_event_ids else True,
        Event.status == 'published',
        Event.event_date >= now
    ).order_by(Event.event_date.asc()).limit(3).all()

    # Participation statistics
    total_registered = len(registrations)
    total_attended = Attendance.query.filter_by(user_id=user.id).count()
    attendance_rate = round((total_attended / total_registered * 100), 1) if total_registered > 0 else 0

    return render_template(
        'student/dashboard.html',
        user=user,
        upcoming_registered_events=upcoming_registered_events,
        joined_clubs=joined_clubs,
        announcements=announcements_query,
        explore_events=explore_events,
        total_registered=total_registered,
        total_attended=total_attended,
        total_clubs=len(joined_clubs),
        attendance_rate=attendance_rate
    )


@student_bp.route('/registrations')
@login_required
def registrations():
    """List of all event registrations for the logged-in student."""
    user = User.query.get_or_404(session['user_id'])
    regs = EventRegistration.query.filter_by(user_id=user.id).order_by(EventRegistration.registered_at.desc()).all()
    
    return render_template('student/my_registrations.html', registrations=regs, now=datetime.utcnow())


@student_bp.route('/clubs')
@login_required
def clubs():
    """List of clubs joined by the student."""
    user = User.query.get_or_404(session['user_id'])
    memberships = ClubMembership.query.filter_by(user_id=user.id).order_by(ClubMembership.joined_at.desc()).all()
    
    return render_template('student/my_clubs.html', memberships=memberships)


@student_bp.route('/notifications')
@login_required
def notifications():
    """Notification inbox for the student."""
    user = User.query.get_or_404(session['user_id'])
    notifs = Notification.query.filter_by(user_id=user.id).order_by(Notification.created_at.desc()).all()
    
    return render_template('student/notifications.html', notifications=notifs)
