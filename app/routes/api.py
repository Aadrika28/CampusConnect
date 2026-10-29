from datetime import datetime
from flask import Blueprint, request, jsonify, session
from app.models import db, User, Event, EventRegistration, Attendance, Notification
from app.decorators import login_required
from app.utils.qr_service import verify_attendance_token
from app.utils.audit import log_audit

api_bp = Blueprint('api', __name__)


@api_bp.route('/attendance/verify', methods=['POST'])
@login_required
def verify_attendance():
    """
    Validates QR scan token or manual registration code and marks attendance.
    Enforces authorization, registration integrity, event mismatch, and single-scan rules.
    """
    user_id = session.get('user_id')
    user_role = session.get('user_role')

    if user_role not in ('club_leader', 'admin'):
        return jsonify({'success': False, 'message': 'Unauthorized: Only club leaders or administrators can record attendance.'}), 403

    data = request.get_json() or {}
    token = data.get('token', '').strip()
    raw_code = data.get('code', '').strip()
    target_event_id = data.get('event_id')

    if not target_event_id:
        return jsonify({'success': False, 'message': 'Target Event ID is required.'}), 400

    try:
        target_event_id = int(target_event_id)
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid Event ID format.'}), 400

    target_event = Event.query.get(target_event_id)
    if not target_event:
        return jsonify({'success': False, 'message': 'Specified event not found.'}), 404

    # Permission check: current user must be leader of this club or an admin
    if user_role != 'admin' and target_event.club.leader_id != user_id:
        return jsonify({'success': False, 'message': f'You are not authorized to mark attendance for {target_event.club.name} events.'}), 403

    registration = None
    verification_method = 'qr_scan'

    # Case 1: Signed cryptographic QR token provided
    if token:
        is_valid, payload = verify_attendance_token(token)
        if not is_valid:
            return jsonify({'success': False, 'message': f'QR Validation Failed: {payload}'}), 400

        # Check payload matches target event
        token_event_id = payload.get('eid')
        token_reg_id = payload.get('rid')
        token_code = payload.get('code')

        if token_event_id != target_event_id:
            token_event = Event.query.get(token_event_id)
            event_name = token_event.title if token_event else f"ID {token_event_id}"
            return jsonify({
                'success': False,
                'message': f'Event Mismatch! This pass was issued for "{event_name}", not "{target_event.title}".'
            }), 400

        registration = EventRegistration.query.get(token_reg_id)
        if not registration or registration.registration_code != token_code:
            return jsonify({'success': False, 'message': 'Invalid or superseded registration record.'}), 400

    # Case 2: Manual Registration Code fallback
    elif raw_code:
        verification_method = 'manual'
        registration = EventRegistration.query.filter_by(
            registration_code=raw_code.upper()
        ).first()

        if not registration:
            return jsonify({'success': False, 'message': f'No registration found with code "{raw_code}".'}), 404

        if registration.event_id != target_event_id:
            return jsonify({
                'success': False,
                'message': f'Code mismatch: This ticket is for "{registration.event.title}".'
            }), 400

    else:
        return jsonify({'success': False, 'message': 'Neither QR token nor registration code provided.'}), 400

    # Validate registration status
    if registration.status != 'confirmed':
        return jsonify({'success': False, 'message': f'Registration status is "{registration.status}". Cannot mark attendance.'}), 400

    # Check duplicate attendance
    existing_attendance = Attendance.query.filter_by(registration_id=registration.id).first()
    if existing_attendance:
        marked_time = existing_attendance.marked_at.strftime('%I:%M %p')
        return jsonify({
            'success': False,
            'duplicate': True,
            'message': f'Attendance was ALREADY marked for {registration.user.name} today at {marked_time}.',
            'student_name': registration.user.name,
            'student_id': registration.user.student_id,
            'marked_at': existing_attendance.marked_at.isoformat()
        }), 409

    # Record attendance
    now = datetime.utcnow()
    attendance = Attendance(
        registration_id=registration.id,
        event_id=target_event.id,
        user_id=registration.user_id,
        marked_by_id=user_id,
        verification_method=verification_method,
        marked_at=now
    )
    db.session.add(attendance)

    # In-app notification for the student
    notification = Notification(
        user_id=registration.user_id,
        title=f"Attendance Confirmed: {target_event.title}",
        message=f"Your attendance for {target_event.title} has been verified and recorded at {now.strftime('%I:%M %p')}.",
        link=f"/events/{target_event.id}"
    )
    db.session.add(notification)

    db.session.commit()

    log_audit('ATTENDANCE_MARKED', 'Attendance', attendance.id, f"Marked attendance for {registration.user.name} at {target_event.title} via {verification_method}", user_id)

    return jsonify({
        'success': True,
        'message': f'Verified! Welcome {registration.user.name}.',
        'student_name': registration.user.name,
        'student_id': registration.user.student_id or 'N/A',
        'department': registration.user.department,
        'event_title': target_event.title,
        'verification_method': verification_method,
        'marked_at': now.strftime('%b %d, %Y - %I:%M:%S %p')
    })


@api_bp.route('/attendance/toggle-manual', methods=['POST'])
@login_required
def toggle_manual_attendance():
    """Toggle attendance status from the participant management table."""
    user_id = session.get('user_id')
    user_role = session.get('user_role')

    if user_role not in ('club_leader', 'admin'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    data = request.get_json() or {}
    registration_id = data.get('registration_id')

    if not registration_id:
        return jsonify({'success': False, 'message': 'Registration ID required'}), 400

    registration = EventRegistration.query.get(registration_id)
    if not registration:
        return jsonify({'success': False, 'message': 'Registration not found'}), 404

    # Permission check
    if user_role != 'admin' and registration.event.club.leader_id != user_id:
        return jsonify({'success': False, 'message': 'Unauthorized for this club'}), 403

    existing_att = Attendance.query.filter_by(registration_id=registration.id).first()

    if existing_att:
        # Remove attendance
        db.session.delete(existing_att)
        db.session.commit()
        log_audit('ATTENDANCE_REMOVED', 'Attendance', existing_att.id, f"Removed attendance for {registration.user.name}", user_id)
        return jsonify({'success': True, 'attended': False, 'message': 'Attendance removed'})
    else:
        # Mark attendance
        now = datetime.utcnow()
        new_att = Attendance(
            registration_id=registration.id,
            event_id=registration.event_id,
            user_id=registration.user_id,
            marked_by_id=user_id,
            verification_method='manual',
            marked_at=now
        )
        db.session.add(new_att)
        db.session.commit()
        log_audit('ATTENDANCE_MARKED', 'Attendance', new_att.id, f"Manually marked attendance for {registration.user.name}", user_id)
        return jsonify({'success': True, 'attended': True, 'message': 'Attendance marked successfully', 'marked_at': now.strftime('%b %d, %Y %I:%M %p')})


@api_bp.route('/notifications/mark-read/<int:notif_id>', methods=['POST'])
@login_required
def mark_notification_read(notif_id):
    """Mark a single notification as read."""
    notif = Notification.query.filter_by(id=notif_id, user_id=session['user_id']).first()
    if notif:
        notif.is_read = True
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Notification not found'}), 404


@api_bp.route('/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    """Mark all notifications for logged-in user as read."""
    Notification.query.filter_by(user_id=session['user_id'], is_read=False).update({'is_read': True})
    db.session.commit()
    return jsonify({'success': True})


@api_bp.route('/events/search')
def search_events_api():
    """Quick search API returning JSON for autocomplete / dropdowns."""
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify([])

    events = Event.query.filter(
        Event.status == 'published',
        Event.title.ilike(f"%{q}%")
    ).limit(8).all()

    return jsonify([
        {
            'id': e.id,
            'title': e.title,
            'category': e.category,
            'club': e.club.name,
            'date': e.event_date.strftime('%b %d, %Y'),
            'url': f"/events/{e.id}"
        }
        for e in events
    ])
