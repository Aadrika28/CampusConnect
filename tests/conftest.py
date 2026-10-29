import pytest
from datetime import datetime, timedelta
from app import create_app
from app.models import db, User, Club, Event, EventRegistration, Attendance


@pytest.fixture
def app():
    """Create application configured for automated testing with in-memory SQLite."""
    test_app = create_app('testing')
    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def seed_data(app):
    """Seed test fixtures: admin, leader, student, sample club, and sample event."""
    with app.app_context():
        # Admin
        admin = User(name="Admin User", student_id="ADM01", email="admin@test.edu", role="admin", is_active=True)
        admin.set_password("Password@123")
        db.session.add(admin)

        # Leader
        leader = User(name="Club Leader", student_id="LEAD01", email="leader@test.edu", role="club_leader", is_active=True)
        leader.set_password("Password@123")
        db.session.add(leader)

        # Student
        student = User(name="Test Student", student_id="STU01", email="student@test.edu", role="student", is_active=True)
        student.set_password("Password@123")
        db.session.add(student)

        # Other Student
        student2 = User(name="Other Student", student_id="STU02", email="student2@test.edu", role="student", is_active=True)
        student2.set_password("Password@123")
        db.session.add(student2)

        db.session.commit()

        # Club
        club = Club(
            name="Computer Science Society",
            slug="cs-society",
            description="Testing club description",
            category="Technical",
            faculty_coordinator="Prof. Turing",
            leader_id=leader.id,
            is_active=True
        )
        db.session.add(club)
        db.session.commit()

        # Event
        now = datetime.utcnow()
        event = Event(
            club_id=club.id,
            title="Spring Hackathon",
            slug="spring-hackathon",
            description="A 24hr test hackathon",
            category="Hackathon",
            venue="Lab 1",
            event_date=now + timedelta(days=5),
            registration_deadline=now + timedelta(days=3),
            max_capacity=2, # Small capacity to easily test full state
            status="published",
            created_by_id=leader.id
        )
        db.session.add(event)

        # Another Event (for mismatch tests)
        event2 = Event(
            club_id=club.id,
            title="Design Thinking Seminar",
            slug="design-thinking-seminar",
            description="Design seminar",
            category="Seminar",
            venue="Hall A",
            event_date=now + timedelta(days=7),
            registration_deadline=now + timedelta(days=5),
            max_capacity=50,
            status="published",
            created_by_id=leader.id
        )
        db.session.add(event2)

        # Expired Event (for deadline tests)
        expired_event = Event(
            club_id=club.id,
            title="Past Robotics Show",
            slug="past-robotics-show",
            description="Concluded event",
            category="Competition",
            venue="Arena",
            event_date=now - timedelta(days=2),
            registration_deadline=now - timedelta(days=4),
            max_capacity=100,
            status="published",
            created_by_id=leader.id
        )
        db.session.add(expired_event)

        db.session.commit()

        return {
            'admin_id': admin.id,
            'leader_id': leader.id,
            'student_id': student.id,
            'student2_id': student2.id,
            'club_id': club.id,
            'event_id': event.id,
            'event2_id': event2.id,
            'expired_event_id': expired_event.id
        }
