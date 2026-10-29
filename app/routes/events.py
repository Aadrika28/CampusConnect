from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
from app.models import db, Event, Club, EventRegistration, Attendance, Announcement, Notification
from app.decorators import login_required
from app.utils.qr_service import generate_attendance_token, generate_qr_base64
from app.utils.audit import log_audit

events_bp = Blueprint('events', __name__)


@events_bp.route('/')
def index():
    """Event directory with comprehensive search, category, club, and date filtering."""
    search_query = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    club_id = request.args.get('club_id', type=int)
    status_filter = request.args.get('status', 'upcoming')

    query = Event.query.filter(Event.status != 'draft')
    now = datetime.utcnow()

    if status_filter == 'upcoming':
        query = query.filter(Event.event_date >= now)
    elif status_filter == 'past':
        query = query.filter(Event.event_date < now)

    if search_query:
        query = query.filter(
            db.or_(
                Event.title.ilike(f"%{search_query}%"),
                Event.description.ilike(f"%{search_query}%"),
                Event.venue.ilike(f"%{search_query}%")
            )
        )

    if category:
        query = query.filter(Event.category == category)

    if club_id:
        query = query.filter(Event.club_id == club_id)

    events = query.order_by(Event.event_date.asc()).all()
    clubs = Club.query.filter_by(is_active=True).order_by(Club.name.asc()).all()
    categories = ['Hackathon', 'Workshop', 'Cultural Fest', 'Seminar', 'Sports Tournament', 'Competition']

    # If logged in, get user's registered event IDs
    user_registered_ids = []
    if 'user_id' in session:
        user_regs = EventRegistration.query.filter_by(
            user_id=session['user_id'],
            status='confirmed'
        ).all()
        user_registered_ids = [r.event_id for r in user_regs]

    return render_template(
        'events/index.html',
        events=events,
        clubs=clubs,
        categories=categories,
        search_query=search_query,
        selected_category=category,
        selected_club_id=club_id,
        selected_status=status_filter,
        user_registered_ids=user_registered_ids
    )


@events_bp.route('/<int:event_id>')
def detail(event_id):
    """Detailed event view."""
    event = Event.query.get_or_404(event_id)
    now = datetime.utcnow()

    # Announcements specific to this event
    event_announcements = Announcement.query.filter_by(event_id=event.id).order_by(Announcement.created_at.desc()).all()

    # User registration status
    user_registration = None
    has_attended = False
    if 'user_id' in session:
        user_registration = EventRegistration.query.filter_by(
            event_id=event.id,
            user_id=session['user_id'],
            status='confirmed'
        ).first()
        if user_registration:
            has_attended = Attendance.query.filter_by(
                event_id=event.id,
                user_id=session['user_id']
            ).first() is not None

    return render_template(
        'events/detail.html',
        event=event,
        now=now,
        announcements=event_announcements,
        user_registration=user_registration,
        has_attended=has_attended
    )


@events_bp.route('/<int:event_id>/register', methods=['POST'])
@login_required
def register(event_id):
    """
    Registers student for an event using a transaction with strict capacity,
    deadline, and duplicate checks.
    """
    user_id = session['user_id']
    now = datetime.utcnow()

    try:
        # Query event inside transaction (using with_for_update on Azure SQL / PostgreSQL)
        event_query = db.session.query(Event).filter_by(id=event_id)
        if db.engine.name != 'sqlite':
            event_query = event_query.with_for_update()
        event = event_query.first()
        if not event:
            flash('Event not found.', 'danger')
            return redirect(url_for('events.index'))

        if event.status != 'published':
            flash('This event is not open for registration.', 'warning')
            return redirect(url_for('events.detail', event_id=event.id))

        if now > event.registration_deadline:
            flash('Registration deadline for this event has passed.', 'danger')
            return redirect(url_for('events.detail', event_id=event.id))

        if now > event.event_date:
            flash('This event has already commenced or concluded.', 'warning')
            return redirect(url_for('events.detail', event_id=event.id))

        # Check existing registration
        existing = EventRegistration.query.filter_by(event_id=event.id, user_id=user_id).first()
        if existing:
            if existing.status == 'confirmed':
                flash('You are already registered for this event.', 'info')
                return redirect(url_for('events.ticket', registration_id=existing.id))
            elif existing.status == 'cancelled':
                # Re-activate registration if seats available
                if event.available_seats <= 0:
                    flash('Sorry, this event is fully booked.', 'danger')
                    return redirect(url_for('events.detail', event_id=event.id))
                existing.status = 'confirmed'
                existing.registered_at = now
                existing.cancelled_at = None
                db.session.commit()
                log_audit('EVENT_REGISTER', 'EventRegistration', existing.id, f"Re-registered for event {event.title}", user_id)
                flash('Registration successfully renewed! Here is your digital pass.', 'success')
                return redirect(url_for('events.ticket', registration_id=existing.id))

        # Check capacity
        if event.available_seats <= 0:
            flash('Sorry, this event has reached maximum capacity.', 'danger')
            return redirect(url_for('events.detail', event_id=event.id))

        # Create new registration
        reg_code = EventRegistration.generate_code()
        registration = EventRegistration(
            event_id=event.id,
            user_id=user_id,
            registration_code=reg_code,
            status='confirmed',
            registered_at=now
        )
        db.session.add(registration)
        db.session.flush()  # Populates registration.id for url_for

        # Create in-app notification
        notification = Notification(
            user_id=user_id,
            title=f"Registration Confirmed: {event.title}",
            message=f"You have successfully registered for {event.title} on {event.event_date.strftime('%b %d, %Y at %I:%M %p')}. View your ticket and QR pass.",
            link=url_for('events.ticket', registration_id=registration.id)
        )
        db.session.add(notification)

        db.session.commit()
        log_audit('EVENT_REGISTER', 'EventRegistration', registration.id, f"Registered for {event.title} (Code: {reg_code})", user_id)

        flash('Registration confirmed! Access your QR pass below.', 'success')
        return redirect(url_for('events.ticket', registration_id=registration.id))

    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred during registration: {str(e)}', 'danger')
        return redirect(url_for('events.detail', event_id=event_id))


@events_bp.route('/<int:event_id>/cancel', methods=['POST'])
@login_required
def cancel_registration(event_id):
    """Allows student to cancel their own registration prior to the event."""
    user_id = session['user_id']
    registration = EventRegistration.query.filter_by(
        event_id=event_id,
        user_id=user_id,
        status='confirmed'
    ).first()

    if not registration:
        flash('No active registration found to cancel.', 'warning')
        return redirect(url_for('student.registrations'))

    # Check if attendance is already recorded
    attendance = Attendance.query.filter_by(registration_id=registration.id).first()
    if attendance:
        flash('Cannot cancel registration: Attendance has already been recorded.', 'danger')
        return redirect(url_for('student.registrations'))

    # Check if event is in the past
    if datetime.utcnow() > registration.event.event_date:
        flash('Cannot cancel registration for a past event.', 'warning')
        return redirect(url_for('student.registrations'))

    registration.status = 'cancelled'
    registration.cancelled_at = datetime.utcnow()
    db.session.commit()

    log_audit('EVENT_CANCEL_REG', 'EventRegistration', registration.id, f"Cancelled registration for event {registration.event.title}", user_id)
    flash(f'Your registration for "{registration.event.title}" has been cancelled.', 'info')
    return redirect(url_for('student.registrations'))


@events_bp.route('/ticket/<int:registration_id>')
@login_required
def ticket(registration_id):
    """Digital Event Pass with QR code verification token."""
    registration = EventRegistration.query.get_or_404(registration_id)
    user_id = session['user_id']
    user_role = session.get('user_role')

    # Security check: only ticket owner, club leader of organizer club, or admin can view ticket
    is_owner = (registration.user_id == user_id)
    is_leader = (user_role == 'club_leader' and registration.event.club.leader_id == user_id)
    is_admin = (user_role == 'admin')

    if not (is_owner or is_leader or is_admin):
        abort(403)

    if registration.status != 'confirmed':
        flash('This registration is no longer active.', 'warning')
        return redirect(url_for('student.registrations'))

    # Generate signed cryptographic attendance token
    token = generate_attendance_token(
        registration_id=registration.id,
        event_id=registration.event_id,
        user_id=registration.user_id,
        registration_code=registration.registration_code
    )

    # Generate QR Code image base64
    qr_b64 = generate_qr_base64(token)

    # Check attendance status
    attendance = Attendance.query.filter_by(registration_id=registration.id).first()

    return render_template(
        'events/ticket.html',
        registration=registration,
        event=registration.event,
        student=registration.user,
        qr_b64=qr_b64,
        attendance_token=token,
        attendance=attendance
    )
