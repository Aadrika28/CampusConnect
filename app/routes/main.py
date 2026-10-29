from datetime import datetime
from flask import Blueprint, render_template, session
from app.models import Event, Club, User, EventRegistration

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """CampusConnect Landing Page."""
    now = datetime.utcnow()
    # Featured / Upcoming events
    featured_events = Event.query.filter(
        Event.status == 'published',
        Event.event_date >= now
    ).order_by(Event.event_date.asc()).limit(6).all()

    # Active clubs
    featured_clubs = Club.query.filter_by(is_active=True).order_by(Club.name.asc()).limit(6).all()

    # Statistics for social proof
    total_students = User.query.filter_by(role='student', is_active=True).count()
    total_clubs = Club.query.filter_by(is_active=True).count()
    total_events = Event.query.filter(Event.status != 'draft').count()
    total_registrations = EventRegistration.query.filter_by(status='confirmed').count()

    return render_template(
        'index.html',
        featured_events=featured_events,
        featured_clubs=featured_clubs,
        total_students=total_students,
        total_clubs=total_clubs,
        total_events=total_events,
        total_registrations=total_registrations
    )


@main_bp.route('/about')
def about():
    """About page explaining CampusConnect architecture and features."""
    return render_template('about.html')
