import os
from datetime import datetime, timedelta
from app import create_app
from app.models import db, User, Club, ClubMembership, Event, EventRegistration, Attendance, Announcement, Notification, AuditLog


def seed_database():
    """Populates database with realistic campus demo accounts, societies, events, and registrations."""
    app = create_app()

    with app.app_context():
        print("Initializing database tables...")
        db.create_all()

        # Check if already seeded
        if User.query.filter_by(email='admin@campus.edu').first():
            print("Database already contains demo seed data. Skipping seed.")
            return

        print("Seeding sample users (Admin, Club Leader, Students)...")
        now = datetime.utcnow()

        # 1. Administrator
        admin = User(
            name="Dr. Eleanor Vance",
            student_id="EMP-ADMIN01",
            email="admin@campus.edu",
            role="admin",
            department="Dean of Student Affairs",
            batch_year=2015,
            phone="+1 (555) 019-2831",
            is_active=True
        )
        admin.set_password("Campus@2025")
        db.session.add(admin)

        # 2. Club Leader
        leader = User(
            name="Rohan Sharma",
            student_id="CS2023001",
            email="leader@campus.edu",
            role="club_leader",
            department="Computer Science & Engineering",
            batch_year=2025,
            phone="+1 (555) 018-9922",
            is_active=True
        )
        leader.set_password("Campus@2025")
        db.session.add(leader)

        # 3. Main Student
        student = User(
            name="Aadrika Pandey",
            student_id="CS2024042",
            email="student@campus.edu",
            role="student",
            department="Computer Science & Engineering",
            batch_year=2026,
            phone="+1 (555) 017-3344",
            is_active=True
        )
        student.set_password("Campus@2025")
        db.session.add(student)

        # Additional Students for Realistic Analytics
        s1 = User(
            name="Marcus Chen",
            student_id="IT2024019",
            email="marcus@campus.edu",
            role="student",
            department="Information Technology",
            batch_year=2026,
            is_active=True
        )
        s1.set_password("Campus@2025")
        db.session.add(s1)

        s2 = User(
            name="Priya Patel",
            student_id="EC2024088",
            email="priya@campus.edu",
            role="student",
            department="Electronics & Communication",
            batch_year=2026,
            is_active=True
        )
        s2.set_password("Campus@2025")
        db.session.add(s2)

        s3 = User(
            name="Alex Rivera",
            student_id="ME2023055",
            email="alex@campus.edu",
            role="student",
            department="Mechanical Engineering",
            batch_year=2025,
            is_active=True
        )
        s3.set_password("Campus@2025")
        db.session.add(s3)

        db.session.commit()
        print("Users created.")

        # 4. Clubs / Societies
        print("Seeding campus clubs...")
        club_acm = Club(
            name="Tech & Coding Society (ACM)",
            slug="tech-coding-society-acm",
            description="The premier student computer science organization dedicated to competitive programming, hackathons, open-source projects, and full-stack software development.",
            category="Technical",
            faculty_coordinator="Dr. Alan Turing",
            leader_id=leader.id,
            is_active=True
        )
        db.session.add(club_acm)

        club_robotics = Club(
            name="Robotics & Autonomous Systems",
            slug="robotics-autonomous-systems",
            description="Engineering cutting-edge robotics, aerial drones, IoT hardware systems, and autonomous ground vehicles for collegiate robotics tournaments.",
            category="Technical",
            faculty_coordinator="Dr. Margaret Hamilton",
            leader_id=leader.id,
            is_active=True
        )
        db.session.add(club_robotics)

        club_cultural = Club(
            name="Natrang Dramatic & Cultural Society",
            slug="natrang-cultural-society",
            description="The flagship cultural society hosting theater productions, stage musicals, classical dance fests, and university-wide cultural extravaganzas.",
            category="Cultural",
            faculty_coordinator="Prof. Laurence Olivier",
            is_active=True
        )
        db.session.add(club_cultural)

        club_sports = Club(
            name="Campus Sports & Athletics Guild",
            slug="campus-sports-athletics-guild",
            description="Fostering athletic excellence, sportsmanship, and fitness through inter-department tournaments in basketball, football, cricket, and badminton.",
            category="Sports",
            faculty_coordinator="Coach Jesse Owens",
            is_active=True
        )
        db.session.add(club_sports)

        club_ecell = Club(
            name="E-Cell (Entrepreneurship Cell)",
            slug="e-cell-entrepreneurship",
            description="Incubating student startup ideas, venture capital pitch days, founder fireside chats, and angel investment hackathons.",
            category="Entrepreneurship",
            faculty_coordinator="Dr. Joseph Schumpeter",
            is_active=True
        )
        db.session.add(club_ecell)

        db.session.commit()
        print("Clubs created.")

        # 5. Club Memberships
        memberships = [
            ClubMembership(club_id=club_acm.id, user_id=leader.id, role='leader'),
            ClubMembership(club_id=club_acm.id, user_id=student.id, role='member'),
            ClubMembership(club_id=club_acm.id, user_id=s1.id, role='core_team'),
            ClubMembership(club_id=club_acm.id, user_id=s2.id, role='member'),
            ClubMembership(club_id=club_robotics.id, user_id=student.id, role='member'),
            ClubMembership(club_id=club_cultural.id, user_id=student.id, role='member'),
            ClubMembership(club_id=club_sports.id, user_id=s3.id, role='member'),
            ClubMembership(club_id=club_ecell.id, user_id=s1.id, role='member'),
            ClubMembership(club_id=club_ecell.id, user_id=s2.id, role='member'),
        ]
        db.session.add_all(memberships)
        db.session.commit()

        # 6. Events
        print("Seeding campus events...")
        event1 = Event(
            club_id=club_acm.id,
            title="HackCamp 2025: 36-Hour National Hackathon",
            slug="hackcamp-2025-national-hackathon",
            description="Join 300+ collegiate innovators in building cutting-edge web, mobile, and cloud applications using Azure AI, Python, and open-source stacks. Free meals, sponsor bounties, and $10,000 in grand prizes!",
            category="Hackathon",
            venue="University Innovation Center - Labs 1 to 4",
            event_date=now + timedelta(days=6, hours=2),
            end_date=now + timedelta(days=7, hours=14),
            registration_deadline=now + timedelta(days=4),
            max_capacity=150,
            status="published",
            created_by_id=leader.id
        )

        event2 = Event(
            club_id=club_acm.id,
            title="Generative AI & LLM Systems Hands-on Workshop",
            slug="generative-ai-llm-systems-workshop",
            description="Deep dive into modern Transformer architectures, prompt engineering, Azure OpenAI service integration, and building full-stack AI agents with Python.",
            category="Workshop",
            venue="CS Auditorium Hall B",
            event_date=now + timedelta(days=10, hours=4),
            end_date=now + timedelta(days=10, hours=7),
            registration_deadline=now + timedelta(days=8),
            max_capacity=80,
            status="published",
            created_by_id=leader.id
        )

        event3 = Event(
            club_id=club_robotics.id,
            title="RoboWars 2025: Autonomous Drone Arena",
            slug="robowars-2025-autonomous-drone-arena",
            description="Collegiate teams pit autonomous mini-drones and battle bots in obstacle navigation and agility challenges.",
            category="Competition",
            venue="Indoor Sports Pavilion",
            event_date=now + timedelta(days=14, hours=3),
            end_date=now + timedelta(days=14, hours=9),
            registration_deadline=now + timedelta(days=11),
            max_capacity=120,
            status="published",
            created_by_id=leader.id
        )

        event4 = Event(
            club_id=club_cultural.id,
            title="Sanskritik 2025: Annual Cultural Fest",
            slug="sanskritik-2025-annual-cultural-fest",
            description="The grand celebration of student performing arts featuring live acoustic music bands, classical theater drama, and inter-college dance face-offs.",
            category="Cultural Fest",
            venue="Open Air University Amphitheater",
            event_date=now + timedelta(days=20, hours=8),
            end_date=now + timedelta(days=21, hours=2),
            registration_deadline=now + timedelta(days=17),
            max_capacity=500,
            status="published",
            created_by_id=admin.id
        )

        event5 = Event(
            club_id=club_ecell.id,
            title="VentureLaunch: Campus Startup Pitch Day",
            slug="venturelaunch-startup-pitch-day",
            description="Present your college startup concept before seasoned angel investors, alumni founders, and incubators for seed funding grant opportunities.",
            category="Competition",
            venue="School of Management Auditorium",
            event_date=now + timedelta(days=12, hours=1),
            end_date=now + timedelta(days=12, hours=6),
            registration_deadline=now + timedelta(days=9),
            max_capacity=100,
            status="published",
            created_by_id=admin.id
        )

        # Past Event with Recorded Attendance (for instant analytics proof)
        event_past = Event(
            club_id=club_acm.id,
            title="Cloud Architecture & Azure SQL Bootcamp",
            slug="cloud-architecture-azure-sql-bootcamp",
            description="Intensive weekend workshop covering relational schema normalization, Azure SQL provisioning, and containerized backend architectures.",
            category="Workshop",
            venue="CS Lab 2",
            event_date=now - timedelta(days=5),
            end_date=now - timedelta(days=5, hours=-4),
            registration_deadline=now - timedelta(days=7),
            max_capacity=50,
            status="completed",
            created_by_id=leader.id
        )

        db.session.add_all([event1, event2, event3, event4, event5, event_past])
        db.session.commit()
        print("Events created.")

        # 7. Registrations
        print("Seeding event registrations...")
        # Student registers for HackCamp
        reg1 = EventRegistration(
            event_id=event1.id,
            user_id=student.id,
            registration_code=EventRegistration.generate_code(),
            status='confirmed',
            registered_at=now - timedelta(days=2)
        )
        # Student registers for GenAI Workshop
        reg2 = EventRegistration(
            event_id=event2.id,
            user_id=student.id,
            registration_code=EventRegistration.generate_code(),
            status='confirmed',
            registered_at=now - timedelta(days=1)
        )
        # Student registered for past bootcamp
        reg_past_student = EventRegistration(
            event_id=event_past.id,
            user_id=student.id,
            registration_code=EventRegistration.generate_code(),
            status='confirmed',
            registered_at=now - timedelta(days=8)
        )
        # Other student registrations
        reg_s1_e1 = EventRegistration(event_id=event1.id, user_id=s1.id, registration_code=EventRegistration.generate_code(), status='confirmed', registered_at=now - timedelta(days=3))
        reg_s2_e1 = EventRegistration(event_id=event1.id, user_id=s2.id, registration_code=EventRegistration.generate_code(), status='confirmed', registered_at=now - timedelta(days=2))
        reg_s3_e1 = EventRegistration(event_id=event1.id, user_id=s3.id, registration_code=EventRegistration.generate_code(), status='confirmed', registered_at=now - timedelta(days=1))
        
        reg_s1_past = EventRegistration(event_id=event_past.id, user_id=s1.id, registration_code=EventRegistration.generate_code(), status='confirmed', registered_at=now - timedelta(days=9))
        reg_s2_past = EventRegistration(event_id=event_past.id, user_id=s2.id, registration_code=EventRegistration.generate_code(), status='confirmed', registered_at=now - timedelta(days=9))
        
        reg_s2_e4 = EventRegistration(event_id=event4.id, user_id=s2.id, registration_code=EventRegistration.generate_code(), status='confirmed', registered_at=now - timedelta(days=1))
        reg_s3_e5 = EventRegistration(event_id=event5.id, user_id=s3.id, registration_code=EventRegistration.generate_code(), status='confirmed', registered_at=now - timedelta(days=2))

        db.session.add_all([reg1, reg2, reg_past_student, reg_s1_e1, reg_s2_e1, reg_s3_e1, reg_s1_past, reg_s2_past, reg_s2_e4, reg_s3_e5])
        db.session.commit()

        # 8. Attendance Records (Past event attendees verified)
        print("Seeding attendance records...")
        att1 = Attendance(
            registration_id=reg_past_student.id,
            event_id=event_past.id,
            user_id=student.id,
            marked_by_id=leader.id,
            verification_method='qr_scan',
            marked_at=now - timedelta(days=5, hours=-1)
        )
        att2 = Attendance(
            registration_id=reg_s1_past.id,
            event_id=event_past.id,
            user_id=s1.id,
            marked_by_id=leader.id,
            verification_method='qr_scan',
            marked_at=now - timedelta(days=5, hours=-1)
        )
        att3 = Attendance(
            registration_id=reg_s2_past.id,
            event_id=event_past.id,
            user_id=s2.id,
            marked_by_id=leader.id,
            verification_method='manual',
            marked_at=now - timedelta(days=5, hours=-1)
        )
        db.session.add_all([att1, att2, att3])

        # 9. Announcements
        print("Seeding announcements...")
        ann_platform = Announcement(
            title="CampusConnect Platform Officially Launched for 2025!",
            content="Welcome to CampusConnect! Discover upcoming college events, join student societies, and check into venues with your paperless QR pass.",
            scope="platform",
            author_id=admin.id,
            priority="urgent",
            created_at=now - timedelta(days=4)
        )
        ann_club = Announcement(
            title="HackCamp 2025 Problem Statements & Team Formation",
            content="Problem statements for HackCamp 2025 will be announced 24 hours prior to commencement. Find your teammates in our Discord and laboratory meetups.",
            scope="club",
            club_id=club_acm.id,
            author_id=leader.id,
            priority="high",
            created_at=now - timedelta(days=2)
        )
        db.session.add_all([ann_platform, ann_club])

        # 10. Student Notifications
        notif1 = Notification(
            user_id=student.id,
            title="Registration Confirmed: HackCamp 2025",
            message=f"You have confirmed your seat for HackCamp 2025. Your QR ticket is ready in your dashboard.",
            link=f"/events/ticket/{reg1.id}",
            created_at=now - timedelta(days=2)
        )
        notif2 = Notification(
            user_id=student.id,
            title="Welcome to CampusConnect!",
            message="Your student profile is active. Browse societies and find events that match your interests.",
            link="/events",
            created_at=now - timedelta(days=4)
        )
        db.session.add_all([notif1, notif2])

        # 11. Audit Logs
        log1 = AuditLog(
            user_id=admin.id,
            action="SYSTEM_INIT",
            entity_type="Platform",
            entity_id="1",
            details="Database schema initialized and seed data loaded successfully.",
            ip_address="127.0.0.1",
            timestamp=now - timedelta(days=5)
        )
        log2 = AuditLog(
            user_id=leader.id,
            action="EVENT_CREATE",
            entity_type="Event",
            entity_id=str(event1.id),
            details=f"Created HackCamp 2025 for {club_acm.name}",
            ip_address="127.0.0.1",
            timestamp=now - timedelta(days=4)
        )
        db.session.add_all([log1, log2])

        db.session.commit()
        print("\n=======================================================")
        print(">>> CampusConnect Database Seeded Successfully!")
        print("=======================================================")
        print("Demo Credentials:")
        print("1. Administrator: admin@campus.edu   / Campus@2025")
        print("2. Club Leader:   leader@campus.edu  / Campus@2025")
        print("3. Student:       student@campus.edu / Campus@2025")
        print("=======================================================\n")


if __name__ == '__main__':
    seed_database()
