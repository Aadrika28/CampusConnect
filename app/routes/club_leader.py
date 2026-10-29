import csv
import io
import re
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort, Response, current_app
from app.models import db, Club, ClubMembership, Event, EventRegistration, Attendance, Announcement, User
from app.decorators import login_required, club_leader_required
from app.utils.storage import upload_media_file
from app.utils.audit import log_audit

club_leader_bp = Blueprint('club_leader', __name__)


def get_authorized_clubs(user_id):
    """Retrieve clubs that the user is authorized to manage."""
    user = User.query.get(user_id)
    if not user:
        return []
    if user.role == 'admin':
        return Club.query.all()
    return Club.query.filter_by(leader_id=user_id).all()


def verify_club_access(user_id, club_id):
    """Ensure user is leader of the club or system admin."""
    user = User.query.get(user_id)
    if user and user.role == 'admin':
        return True
    club = Club.query.get(club_id)
    return club is not None and club.leader_id == user_id


def slugify(text):
    text = re.sub(r'[^\w\s-]', '', text.lower())
    return re.sub(r'[-\s]+', '-', text).strip('-')


@club_leader_bp.route('/dashboard')
@login_required
@club_leader_required
def dashboard():
    """Club Leader Dashboard with metrics for managed clubs."""
    user_id = session['user_id']
    managed_clubs = get_authorized_clubs(user_id)
    managed_club_ids = [c.id for c in managed_clubs]

    if not managed_clubs:
        flash('You are not currently designated as the leader of any active clubs.', 'warning')

    # Gather metrics across managed clubs
    now = datetime.utcnow()
    total_members = ClubMembership.query.filter(ClubMembership.club_id.in_(managed_club_ids)).count() if managed_club_ids else 0
    
    events_query = Event.query.filter(Event.club_id.in_(managed_club_ids)) if managed_club_ids else []
    total_events = events_query.count() if managed_club_ids else 0
    upcoming_events = events_query.filter(Event.event_date >= now, Event.status == 'published').order_by(Event.event_date.asc()).all() if managed_club_ids else []
    
    # Registration & attendance statistics
    event_ids = [e.id for e in events_query.all()] if managed_club_ids else []
    total_registrations = EventRegistration.query.filter(EventRegistration.event_id.in_(event_ids), EventRegistration.status == 'confirmed').count() if event_ids else 0
    total_attendance = Attendance.query.filter(Attendance.event_id.in_(event_ids)).count() if event_ids else 0
    overall_attendance_rate = round((total_attendance / total_registrations * 100), 1) if total_registrations > 0 else 0

    return render_template(
        'club_leader/dashboard.html',
        managed_clubs=managed_clubs,
        total_members=total_members,
        total_events=total_events,
        upcoming_events=upcoming_events,
        total_registrations=total_registrations,
        total_attendance=total_attendance,
        overall_attendance_rate=overall_attendance_rate
    )


@club_leader_bp.route('/clubs/<int:club_id>/edit', methods=['GET', 'POST'])
@login_required
@club_leader_required
def edit_club(club_id):
    """Edit club profile information and upload logo."""
    if not verify_club_access(session['user_id'], club_id):
        abort(403)

    club = Club.query.get_or_404(club_id)

    if request.method == 'POST':
        club.description = request.form.get('description', '').strip()
        club.category = request.form.get('category', '').strip()
        club.faculty_coordinator = request.form.get('faculty_coordinator', '').strip()

        # Handle Logo file upload (Azure Blob Storage or local fallback)
        logo_file = request.files.get('logo_file')
        if logo_file and logo_file.filename:
            try:
                logo_url = upload_media_file(logo_file, folder_prefix='clubs')
                if logo_url:
                    club.logo_url = logo_url
            except Exception as e:
                flash(f'Logo upload failed: {str(e)}', 'warning')

        db.session.commit()
        log_audit('CLUB_UPDATE', 'Club', club.id, f"Updated club details for {club.name}")
        flash('Club information updated successfully!', 'success')
        return redirect(url_for('club_leader.dashboard'))

    categories = ['Technical', 'Cultural', 'Sports', 'Literary', 'Social Welfare', 'Entrepreneurship']
    return render_template('club_leader/club_edit.html', club=club, categories=categories)


@club_leader_bp.route('/events/new', methods=['GET', 'POST'])
@login_required
@club_leader_required
def create_event():
    """Create a new event under an authorized club."""
    user_id = session['user_id']
    managed_clubs = get_authorized_clubs(user_id)

    if not managed_clubs:
        flash('You must be assigned to at least one club to create events.', 'danger')
        return redirect(url_for('club_leader.dashboard'))

    if request.method == 'POST':
        club_id = request.form.get('club_id', type=int)
        if not verify_club_access(user_id, club_id):
            abort(403)

        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '').strip()
        venue = request.form.get('venue', '').strip()
        event_date_str = request.form.get('event_date')
        end_date_str = request.form.get('end_date')
        deadline_str = request.form.get('registration_deadline')
        max_capacity = request.form.get('max_capacity', type=int) or 100
        status = request.form.get('status', 'published')

        # Parse date fields
        try:
            event_date = datetime.strptime(event_date_str, '%Y-%m-%dT%H:%M')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M') if end_date_str else None
            deadline = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M')
        except (ValueError, TypeError):
            flash('Invalid date or time format provided.', 'danger')
            return render_template('club_leader/event_form.html', managed_clubs=managed_clubs, event=None)

        if deadline > event_date:
            flash('Registration deadline must be set before the event start time.', 'danger')
            return render_template('club_leader/event_form.html', managed_clubs=managed_clubs, event=None)

        # Generate unique slug
        base_slug = slugify(title)
        slug = base_slug
        count = 1
        while Event.query.filter_by(slug=slug).first():
            slug = f"{base_slug}-{count}"
            count += 1

        # Handle banner upload (Azure Blob or local fallback)
        banner_url = None
        banner_file = request.files.get('banner_file')
        if banner_file and banner_file.filename:
            try:
                banner_url = upload_media_file(banner_file, folder_prefix='events')
            except Exception as e:
                flash(f'Banner image upload failed: {str(e)}', 'warning')

        new_event = Event(
            club_id=club_id,
            title=title,
            slug=slug,
            description=description,
            category=category,
            venue=venue,
            event_date=event_date,
            end_date=end_date,
            registration_deadline=deadline,
            max_capacity=max_capacity,
            banner_url=banner_url,
            status=status,
            created_by_id=user_id
        )

        db.session.add(new_event)
        db.session.commit()

        log_audit('EVENT_CREATE', 'Event', new_event.id, f"Created event '{title}' for club ID {club_id}")
        flash(f'Event "{title}" created successfully!', 'success')
        return redirect(url_for('events.detail', event_id=new_event.id))

    categories = ['Hackathon', 'Workshop', 'Cultural Fest', 'Seminar', 'Sports Tournament', 'Competition']
    return render_template('club_leader/event_form.html', managed_clubs=managed_clubs, event=None, categories=categories)


@club_leader_bp.route('/events/<int:event_id>/edit', methods=['GET', 'POST'])
@login_required
@club_leader_required
def edit_event(event_id):
    """Edit existing event."""
    event = Event.query.get_or_404(event_id)
    if not verify_club_access(session['user_id'], event.club_id):
        abort(403)

    user_id = session['user_id']
    managed_clubs = get_authorized_clubs(user_id)

    if request.method == 'POST':
        event.title = request.form.get('title', '').strip()
        event.description = request.form.get('description', '').strip()
        event.category = request.form.get('category', '').strip()
        event.venue = request.form.get('venue', '').strip()
        event.max_capacity = request.form.get('max_capacity', type=int) or event.max_capacity
        event.status = request.form.get('status', event.status)

        event_date_str = request.form.get('event_date')
        end_date_str = request.form.get('end_date')
        deadline_str = request.form.get('registration_deadline')

        try:
            event.event_date = datetime.strptime(event_date_str, '%Y-%m-%dT%H:%M')
            event.end_date = datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M') if end_date_str else None
            event.registration_deadline = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M')
        except (ValueError, TypeError):
            flash('Invalid date or time format.', 'danger')
            return redirect(url_for('club_leader.edit_event', event_id=event.id))

        # Check for banner update
        banner_file = request.files.get('banner_file')
        if banner_file and banner_file.filename:
            try:
                banner_url = upload_media_file(banner_file, folder_prefix='events')
                if banner_url:
                    event.banner_url = banner_url
            except Exception as e:
                flash(f'Banner image upload failed: {str(e)}', 'warning')

        db.session.commit()
        log_audit('EVENT_UPDATE', 'Event', event.id, f"Updated event '{event.title}'")
        flash('Event details updated successfully!', 'success')
        return redirect(url_for('events.detail', event_id=event.id))

    categories = ['Hackathon', 'Workshop', 'Cultural Fest', 'Seminar', 'Sports Tournament', 'Competition']
    return render_template('club_leader/event_form.html', managed_clubs=managed_clubs, event=event, categories=categories)


@club_leader_bp.route('/events/<int:event_id>/participants')
@login_required
@club_leader_required
def participants(event_id):
    """View registered attendees list, search, and manual check-in."""
    event = Event.query.get_or_404(event_id)
    if not verify_club_access(session['user_id'], event.club_id):
        abort(403)

    search_query = request.args.get('q', '').strip()
    status_filter = request.args.get('status', 'all')

    query = EventRegistration.query.filter_by(event_id=event.id)

    if status_filter != 'all':
        query = query.filter_by(status=status_filter)

    if search_query:
        query = query.join(User).filter(
            db.or_(
                User.name.ilike(f"%{search_query}%"),
                User.student_id.ilike(f"%{search_query}%"),
                User.email.ilike(f"%{search_query}%"),
                EventRegistration.registration_code.ilike(f"%{search_query}%")
            )
        )

    registered_list = query.order_by(EventRegistration.registered_at.desc()).all()
    attended_reg_ids = {a.registration_id for a in event.attendances}

    return render_template(
        'club_leader/participants.html',
        event=event,
        participants=registered_list,
        attended_reg_ids=attended_reg_ids,
        search_query=search_query,
        status_filter=status_filter
    )


@club_leader_bp.route('/events/<int:event_id>/export-csv')
@login_required
@club_leader_required
def export_participants_csv(event_id):
    """Export event participants and attendance status to CSV."""
    event = Event.query.get_or_404(event_id)
    if not verify_club_access(session['user_id'], event.club_id):
        abort(403)

    registrations = EventRegistration.query.filter_by(event_id=event.id).all()
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(['Registration Code', 'Student ID', 'Student Name', 'Email', 'Department', 'Status', 'Registered At', 'Attended', 'Attendance Time', 'Verification Method'])

    for reg in registrations:
        att = reg.attendance
        writer.writerow([
            reg.registration_code,
            reg.user.student_id or 'N/A',
            reg.user.name,
            reg.user.email,
            reg.user.department,
            reg.status,
            reg.registered_at.strftime('%Y-%m-%d %H:%M:%S'),
            'Yes' if att else 'No',
            att.marked_at.strftime('%Y-%m-%d %H:%M:%S') if att else '',
            att.verification_method if att else ''
        ])

    csv_data = output.getvalue()
    filename = f"participants_{slugify(event.title)}_{datetime.utcnow().strftime('%Y%m%d')}.csv"

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )


@club_leader_bp.route('/scanner')
@login_required
@club_leader_required
def qr_scanner():
    """Browser-based QR camera scanner page with instant validation & manual fallback."""
    user_id = session['user_id']
    managed_clubs = get_authorized_clubs(user_id)
    managed_club_ids = [c.id for c in managed_clubs]

    # Events available to scan for
    events = Event.query.filter(
        Event.club_id.in_(managed_club_ids),
        Event.status == 'published'
    ).order_by(Event.event_date.desc()).all() if managed_club_ids else []

    selected_event_id = request.args.get('event_id', type=int)
    if not selected_event_id and events:
        selected_event_id = events[0].id

    return render_template(
        'club_leader/qr_scanner.html',
        events=events,
        selected_event_id=selected_event_id
    )


@club_leader_bp.route('/announcements', methods=['GET', 'POST'])
@login_required
@club_leader_required
def announcements():
    """Create and manage club-level announcements."""
    user_id = session['user_id']
    managed_clubs = get_authorized_clubs(user_id)
    managed_club_ids = [c.id for c in managed_clubs]

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        club_id = request.form.get('club_id', type=int)
        priority = request.form.get('priority', 'normal')

        if not verify_club_access(user_id, club_id):
            abort(403)

        new_ann = Announcement(
            title=title,
            content=content,
            scope='club',
            club_id=club_id,
            author_id=user_id,
            priority=priority
        )
        db.session.add(new_ann)
        db.session.commit()

        log_audit('ANNOUNCEMENT_CREATE', 'Announcement', new_ann.id, f"Created announcement '{title}' for club ID {club_id}")
        flash('Club announcement published successfully!', 'success')
        return redirect(url_for('club_leader.announcements'))

    announcements_list = Announcement.query.filter(
        Announcement.club_id.in_(managed_club_ids)
    ).order_by(Announcement.created_at.desc()).all() if managed_club_ids else []

    return render_template(
        'club_leader/announcements.html',
        managed_clubs=managed_clubs,
        announcements=announcements_list
    )
