import csv
import io
from datetime import datetime
from flask import Blueprint, render_template, jsonify, Response, current_app
from sqlalchemy import func
from app.models import db, User, Club, ClubMembership, Event, EventRegistration, Attendance
from app.decorators import login_required, club_leader_required

analytics_bp = Blueprint('analytics', __name__)


@analytics_bp.route('/')
@login_required
@club_leader_required
def index():
    """Interactive Analytics Dashboard with Chart.js visualization."""
    power_bi_url = current_app.config.get('POWER_BI_EMBED_URL')
    
    # Platform summary aggregates
    total_users = User.query.filter_by(role='student').count()
    total_events = Event.query.count()
    total_registrations = EventRegistration.query.filter_by(status='confirmed').count()
    total_attendance = Attendance.query.count()
    overall_attendance_rate = round((total_attendance / total_registrations * 100), 1) if total_registrations > 0 else 0

    return render_template(
        'analytics/index.html',
        total_users=total_users,
        total_events=total_events,
        total_registrations=total_registrations,
        total_attendance=total_attendance,
        overall_attendance_rate=overall_attendance_rate,
        power_bi_url=power_bi_url
    )


@analytics_bp.route('/data')
@login_required
@club_leader_required
def get_chart_data():
    """Provides structured JSON payloads for frontend Chart.js charts."""
    # 1. Registrations by Category
    category_data = db.session.query(
        Event.category,
        func.count(EventRegistration.id)
    ).join(EventRegistration, Event.id == EventRegistration.event_id)\
     .filter(EventRegistration.status == 'confirmed')\
     .group_by(Event.category).all()

    categories_labels = [c[0] for c in category_data]
    categories_counts = [c[1] for c in category_data]

    # 2. Top Popular Events (by registrations)
    top_events = db.session.query(
        Event.title,
        func.count(EventRegistration.id).label('reg_count')
    ).join(EventRegistration, Event.id == EventRegistration.event_id)\
     .filter(EventRegistration.status == 'confirmed')\
     .group_by(Event.id)\
     .order_by(func.count(EventRegistration.id).desc())\
     .limit(6).all()

    top_events_labels = [e[0] for e in top_events]
    top_events_counts = [e[1] for e in top_events]

    # 3. Club Membership Distribution
    club_members = db.session.query(
        Club.name,
        func.count(ClubMembership.id)
    ).join(ClubMembership, Club.id == ClubMembership.club_id)\
     .group_by(Club.id)\
     .order_by(func.count(ClubMembership.id).desc())\
     .limit(7).all()

    club_labels = [c[0] for c in club_members]
    club_counts = [c[1] for c in club_members]

    # 4. Registrations vs Actual Attendance per Event
    event_performance = db.session.query(
        Event.title,
        func.count(EventRegistration.id).label('regs'),
        func.count(Attendance.id).label('attends')
    ).outerjoin(EventRegistration, db.and_(Event.id == EventRegistration.event_id, EventRegistration.status == 'confirmed'))\
     .outerjoin(Attendance, Event.id == Attendance.event_id)\
     .group_by(Event.id)\
     .order_by(Event.event_date.desc())\
     .limit(6).all()

    perf_labels = [p[0][:20] + ('...' if len(p[0]) > 20 else '') for p in event_performance]
    perf_regs = [p[1] for p in event_performance]
    perf_attends = [p[2] for p in event_performance]

    return jsonify({
        'categories': {
            'labels': categories_labels or ['Hackathon', 'Workshop', 'Cultural Fest'],
            'counts': categories_counts or [0, 0, 0]
        },
        'top_events': {
            'labels': top_events_labels or ['No Data'],
            'counts': top_events_counts or [0]
        },
        'club_members': {
            'labels': club_labels or ['No Clubs'],
            'counts': club_counts or [0]
        },
        'performance': {
            'labels': perf_labels or ['No Events'],
            'registrations': perf_regs or [0],
            'attendance': perf_attends or [0]
        }
    })


@analytics_bp.route('/export/registrations.csv')
@login_required
@club_leader_required
def export_registrations_csv():
    """Export all registration records for Power BI or Excel analysis."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Registration ID', 'Registration Code', 'Event Title', 'Event Category', 'Club Name', 'Student ID', 'Student Name', 'Department', 'Batch Year', 'Status', 'Registered At'])

    regs = EventRegistration.query.join(Event).join(User).all()
    for r in regs:
        writer.writerow([
            r.id,
            r.registration_code,
            r.event.title,
            r.event.category,
            r.event.club.name,
            r.user.student_id or 'N/A',
            r.user.name,
            r.user.department,
            r.user.batch_year,
            r.status,
            r.registered_at.strftime('%Y-%m-%d %H:%M:%S')
        ])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=campusconnect_registrations_{datetime.utcnow().strftime('%Y%m%d')}.csv"}
    )


@analytics_bp.route('/export/attendance.csv')
@login_required
@club_leader_required
def export_attendance_csv():
    """Export attendance verification dataset for Power BI."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Attendance ID', 'Event Title', 'Club Name', 'Student ID', 'Student Name', 'Department', 'Verification Method', 'Marked By', 'Marked At'])

    records = Attendance.query.join(Event).join(User, Attendance.user_id == User.id).all()
    for a in records:
        writer.writerow([
            a.id,
            a.event.title,
            a.event.club.name,
            a.user.student_id or 'N/A',
            a.user.name,
            a.user.department,
            a.verification_method,
            a.marked_by.name if a.marked_by else 'System',
            a.marked_at.strftime('%Y-%m-%d %H:%M:%S')
        ])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=campusconnect_attendance_{datetime.utcnow().strftime('%Y%m%d')}.csv"}
    )


@analytics_bp.route('/export/clubs_summary.csv')
@login_required
@club_leader_required
def export_clubs_summary_csv():
    """Export club participation summary dataset."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Club ID', 'Club Name', 'Category', 'Faculty Coordinator', 'Leader Name', 'Total Members', 'Total Events Organized', 'Status'])

    clubs = Club.query.all()
    for c in clubs:
        writer.writerow([
            c.id,
            c.name,
            c.category,
            c.faculty_coordinator,
            c.leader.name if c.leader else 'Unassigned',
            c.member_count,
            len(c.events),
            'Active' if c.is_active else 'Inactive'
        ])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=campusconnect_clubs_{datetime.utcnow().strftime('%Y%m%d')}.csv"}
    )
