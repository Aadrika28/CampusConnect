from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models import db, Club, ClubMembership, Event, Announcement, Notification
from app.decorators import login_required
from app.utils.audit import log_audit

clubs_bp = Blueprint('clubs', __name__)


@clubs_bp.route('/')
def index():
    """Club directory with search and category filtering."""
    search_query = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()

    query = Club.query.filter_by(is_active=True)

    if search_query:
        query = query.filter(
            db.or_(
                Club.name.ilike(f"%{search_query}%"),
                Club.description.ilike(f"%{search_query}%"),
                Club.faculty_coordinator.ilike(f"%{search_query}%")
            )
        )

    if category:
        query = query.filter(Club.category == category)

    clubs = query.order_by(Club.name.asc()).all()
    categories = ['Technical', 'Cultural', 'Sports', 'Literary', 'Social Welfare', 'Entrepreneurship']

    # Get clubs the current user is already a member of
    user_club_ids = []
    if 'user_id' in session:
        memberships = ClubMembership.query.filter_by(user_id=session['user_id']).all()
        user_club_ids = [m.club_id for m in memberships]

    return render_template(
        'clubs/index.html',
        clubs=clubs,
        categories=categories,
        search_query=search_query,
        selected_category=category,
        user_club_ids=user_club_ids
    )


@clubs_bp.route('/<int:club_id>')
def detail(club_id):
    """Club profile showing description, coordinator, upcoming events, and announcements."""
    club = Club.query.get_or_404(club_id)
    now = datetime.utcnow()

    # Club events
    upcoming_events = Event.query.filter(
        Event.club_id == club.id,
        Event.status == 'published',
        Event.event_date >= now
    ).order_by(Event.event_date.asc()).all()

    past_events = Event.query.filter(
        Event.club_id == club.id,
        Event.status == 'published',
        Event.event_date < now
    ).order_by(Event.event_date.desc()).limit(6).all()

    # Club announcements
    announcements = Announcement.query.filter_by(club_id=club.id).order_by(Announcement.created_at.desc()).all()

    # Check membership status for current user
    is_member = False
    membership_role = None
    if 'user_id' in session:
        membership = ClubMembership.query.filter_by(club_id=club.id, user_id=session['user_id']).first()
        if membership:
            is_member = True
            membership_role = membership.role

    return render_template(
        'clubs/detail.html',
        club=club,
        upcoming_events=upcoming_events,
        past_events=past_events,
        announcements=announcements,
        is_member=is_member,
        membership_role=membership_role
    )


@clubs_bp.route('/<int:club_id>/join', methods=['POST'])
@login_required
def join(club_id):
    """Student joins a club."""
    user_id = session['user_id']
    club = Club.query.get_or_404(club_id)

    if not club.is_active:
        flash('This club is currently inactive.', 'warning')
        return redirect(url_for('clubs.detail', club_id=club.id))

    # Check duplicate membership
    existing = ClubMembership.query.filter_by(club_id=club.id, user_id=user_id).first()
    if existing:
        flash(f'You are already a member of {club.name}.', 'info')
        return redirect(url_for('clubs.detail', club_id=club.id))

    membership = ClubMembership(
        club_id=club.id,
        user_id=user_id,
        role='member'
    )
    db.session.add(membership)

    # In-app notification
    notification = Notification(
        user_id=user_id,
        title=f"Welcome to {club.name}!",
        message=f"You are now an official member of {club.name}. Stay tuned for upcoming activities and workshops.",
        link=url_for('clubs.detail', club_id=club.id)
    )
    db.session.add(notification)

    db.session.commit()
    log_audit('CLUB_JOIN', 'ClubMembership', membership.id, f"Joined club {club.name}", user_id)

    flash(f'Congratulations! You have joined {club.name}.', 'success')
    return redirect(url_for('clubs.detail', club_id=club.id))


@clubs_bp.route('/<int:club_id>/leave', methods=['POST'])
@login_required
def leave(club_id):
    """Student leaves a club."""
    user_id = session['user_id']
    club = Club.query.get_or_404(club_id)

    membership = ClubMembership.query.filter_by(club_id=club.id, user_id=user_id).first()
    if not membership:
        flash('You are not a member of this club.', 'warning')
        return redirect(url_for('clubs.detail', club_id=club.id))

    if membership.role == 'leader':
        flash('Club leaders cannot leave the club directly. Please assign a new leader through administration.', 'danger')
        return redirect(url_for('clubs.detail', club_id=club.id))

    db.session.delete(membership)
    db.session.commit()

    log_audit('CLUB_LEAVE', 'ClubMembership', club_id, f"Left club {club.name}", user_id)
    flash(f'You have left {club.name}.', 'info')
    return redirect(url_for('student.clubs'))
