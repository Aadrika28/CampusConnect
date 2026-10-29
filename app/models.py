from datetime import datetime
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    """User account representing Students, Club Leaders, or Administrators."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(50), unique=True, nullable=True, index=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='student', nullable=False)  # student, club_leader, admin
    department = db.Column(db.String(100), default='Computer Science')
    batch_year = db.Column(db.Integer, default=2025)
    phone = db.Column(db.String(20), nullable=True)
    avatar_url = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    led_clubs = db.relationship('Club', back_populates='leader', foreign_keys='Club.leader_id')
    memberships = db.relationship('ClubMembership', back_populates='user', cascade='all, delete-orphan')
    registrations = db.relationship('EventRegistration', back_populates='user', cascade='all, delete-orphan')
    attendances = db.relationship('Attendance', back_populates='user', foreign_keys='Attendance.user_id', cascade='all, delete-orphan')
    notifications = db.relationship('Notification', back_populates='user', cascade='all, delete-orphan', order_by='Notification.created_at.desc()')
    audit_logs = db.relationship('AuditLog', back_populates='user', foreign_keys='AuditLog.user_id')

    def set_password(self, password):
        """Secure password hashing using Werkzeug generate_password_hash."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify password against hashed value."""
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_club_leader(self):
        return self.role in ('club_leader', 'admin')

    @property
    def is_student(self):
        return self.role == 'student'

    def unread_notifications_count(self):
        return Notification.query.filter_by(user_id=self.id, is_read=False).count()

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'department': self.department,
            'batch_year': self.batch_year,
            'phone': self.phone,
            'avatar_url': self.avatar_url,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Club(db.Model):
    """Student organization, society, or department club."""
    __tablename__ = 'clubs'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)  # Technical, Cultural, Sports, Literary, Social, Entrepreneurship
    logo_url = db.Column(db.String(255), nullable=True)
    banner_url = db.Column(db.String(255), nullable=True)
    faculty_coordinator = db.Column(db.String(100), nullable=False)
    leader_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    leader = db.relationship('User', back_populates='led_clubs', foreign_keys=[leader_id])
    memberships = db.relationship('ClubMembership', back_populates='club', cascade='all, delete-orphan')
    events = db.relationship('Event', back_populates='club', cascade='all, delete-orphan')
    announcements = db.relationship('Announcement', back_populates='club', cascade='all, delete-orphan')

    @property
    def member_count(self):
        return len(self.memberships)

    @property
    def active_events_count(self):
        now = datetime.utcnow()
        return len([e for e in self.events if e.status == 'published' and e.event_date >= now])

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'category': self.category,
            'logo_url': self.logo_url,
            'faculty_coordinator': self.faculty_coordinator,
            'leader_name': self.leader.name if self.leader else 'Unassigned',
            'member_count': self.member_count,
            'is_active': self.is_active
        }


class ClubMembership(db.Model):
    """Membership association between Student and Club."""
    __tablename__ = 'club_memberships'
    __table_args__ = (
        db.UniqueConstraint('club_id', 'user_id', name='uq_club_user'),
    )

    id = db.Column(db.Integer, primary_key=True)
    club_id = db.Column(db.Integer, db.ForeignKey('clubs.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    role = db.Column(db.String(30), default='member', nullable=False)  # member, core_team, leader
    joined_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    club = db.relationship('Club', back_populates='memberships')
    user = db.relationship('User', back_populates='memberships')


class Event(db.Model):
    """Campus event organized by a club or college committee."""
    __tablename__ = 'events'

    id = db.Column(db.Integer, primary_key=True)
    club_id = db.Column(db.Integer, db.ForeignKey('clubs.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(150), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)  # Hackathon, Workshop, Cultural Fest, Seminar, Sports Tournament, Competition
    venue = db.Column(db.String(150), nullable=False)
    event_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=True)
    registration_deadline = db.Column(db.DateTime, nullable=False)
    max_capacity = db.Column(db.Integer, nullable=False, default=100)
    banner_url = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), default='published', nullable=False)  # draft, published, cancelled, completed
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    club = db.relationship('Club', back_populates='events')
    creator = db.relationship('User', foreign_keys=[created_by_id])
    registrations = db.relationship('EventRegistration', back_populates='event', cascade='all, delete-orphan')
    attendances = db.relationship('Attendance', back_populates='event', cascade='all, delete-orphan')
    announcements = db.relationship('Announcement', back_populates='event', cascade='all, delete-orphan')

    @property
    def confirmed_registrations(self):
        return [r for r in self.registrations if r.status == 'confirmed']

    @property
    def confirmed_registrations_count(self):
        return len(self.confirmed_registrations)

    @property
    def attended_count(self):
        return len(self.attendances)

    @property
    def available_seats(self):
        return max(0, self.max_capacity - self.confirmed_registrations_count)

    @property
    def is_full(self):
        return self.confirmed_registrations_count >= self.max_capacity

    @property
    def is_past_deadline(self):
        return datetime.utcnow() > self.registration_deadline

    @property
    def is_past_event(self):
        return datetime.utcnow() > (self.end_date or self.event_date)

    @property
    def can_register(self):
        return (
            self.status == 'published'
            and not self.is_full
            and not self.is_past_deadline
            and not self.is_past_event
        )

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'slug': self.slug,
            'description': self.description,
            'category': self.category,
            'venue': self.venue,
            'event_date': self.event_date.isoformat(),
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'registration_deadline': self.registration_deadline.isoformat(),
            'max_capacity': self.max_capacity,
            'available_seats': self.available_seats,
            'banner_url': self.banner_url,
            'status': self.status,
            'club_name': self.club.name if self.club else None,
            'club_id': self.club_id,
            'can_register': self.can_register
        }


class EventRegistration(db.Model):
    """Student registration record for an event."""
    __tablename__ = 'event_registrations'
    __table_args__ = (
        db.UniqueConstraint('event_id', 'user_id', name='uq_event_user'),
    )

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    registration_code = db.Column(db.String(64), unique=True, nullable=False, index=True)
    status = db.Column(db.String(20), default='confirmed', nullable=False)  # confirmed, cancelled
    registered_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    cancelled_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    event = db.relationship('Event', back_populates='registrations')
    user = db.relationship('User', back_populates='registrations')
    attendance = db.relationship('Attendance', back_populates='registration', uselist=False, cascade='all, delete-orphan')

    @classmethod
    def generate_code(cls):
        """Generate cryptographically unique registration code."""
        return f"REG-{uuid.uuid4().hex[:12].upper()}"


class Attendance(db.Model):
    """Attendance verification record for an event participant."""
    __tablename__ = 'attendance'
    __table_args__ = (
        db.UniqueConstraint('event_id', 'user_id', name='uq_attendance_event_user'),
    )

    id = db.Column(db.Integer, primary_key=True)
    registration_id = db.Column(db.Integer, db.ForeignKey('event_registrations.id', ondelete='CASCADE'), unique=True, nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    marked_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    verification_method = db.Column(db.String(20), default='qr_scan', nullable=False)  # qr_scan, manual
    marked_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    registration = db.relationship('EventRegistration', back_populates='attendance')
    event = db.relationship('Event', back_populates='attendances')
    user = db.relationship('User', back_populates='attendances', foreign_keys=[user_id])
    marked_by = db.relationship('User', foreign_keys=[marked_by_id])


class Announcement(db.Model):
    """Notice or update published across the platform, by club, or for a specific event."""
    __tablename__ = 'announcements'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    scope = db.Column(db.String(20), default='platform', nullable=False)  # platform, club, event
    club_id = db.Column(db.Integer, db.ForeignKey('clubs.id', ondelete='CASCADE'), nullable=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id', ondelete='CASCADE'), nullable=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    priority = db.Column(db.String(20), default='normal', nullable=False)  # low, normal, high, urgent
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    club = db.relationship('Club', back_populates='announcements')
    event = db.relationship('Event', back_populates='announcements')
    author = db.relationship('User')


class Notification(db.Model):
    """Personalized user notification message."""
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    link = db.Column(db.String(255), nullable=True)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = db.relationship('User', back_populates='notifications')


class AuditLog(db.Model):
    """Platform audit trail for security and governance."""
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    action = db.Column(db.String(50), nullable=False)  # USER_LOGIN, EVENT_CREATED, ATTENDANCE_MARKED, etc.
    entity_type = db.Column(db.String(50), nullable=False)  # User, Event, Registration, Club, Attendance
    entity_id = db.Column(db.String(50), nullable=True)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = db.relationship('User', back_populates='audit_logs', foreign_keys=[user_id])
