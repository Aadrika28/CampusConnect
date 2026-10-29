from app.models import Event, EventRegistration, db


def login_student(client):
    client.post('/auth/login', data={'email': 'student@test.edu', 'password': 'Password@123'}, follow_redirects=True)


def login_student2(client):
    client.post('/auth/login', data={'email': 'student2@test.edu', 'password': 'Password@123'}, follow_redirects=True)


def test_event_listing_and_detail(client, seed_data):
    """Catalog renders events, categories, and allows searching."""
    res = client.get('/events/')
    assert res.status_code == 200
    assert b"Spring Hackathon" in res.data

    # Search filter
    res_search = client.get('/events/?q=Hackathon')
    assert b"Spring Hackathon" in res_search.data
    assert b"Design Thinking" not in res_search.data

    # Event detail
    res_detail = client.get(f"/events/{seed_data['event_id']}")
    assert res_detail.status_code == 200
    assert b"About This Event" in res_detail.data


def test_event_registration_flow(client, app, seed_data):
    """Student registers for an open event and generates ticket."""
    login_student(client)

    event_id = seed_data['event_id']
    res = client.post(f"/events/{event_id}/register", follow_redirects=True)
    assert res.status_code == 200
    assert b"Official CampusConnect Event Pass" in res.data

    with app.app_context():
        reg = EventRegistration.query.filter_by(event_id=event_id, user_id=seed_data['student_id']).first()
        assert reg is not None
        assert reg.status == 'confirmed'
        assert reg.registration_code.startswith('REG-')


def test_duplicate_event_registration(client, app, seed_data):
    """Student cannot double-book the same event."""
    login_student(client)
    event_id = seed_data['event_id']

    # First registration
    client.post(f"/events/{event_id}/register", follow_redirects=True)

    # Second attempt
    res2 = client.post(f"/events/{event_id}/register", follow_redirects=True)
    assert b"already registered" in res2.data


def test_event_capacity_limit(client, app, seed_data):
    """Event with capacity 2 rejects a third registrant."""
    event_id = seed_data['event_id'] # max_capacity = 2

    # Registrant 1
    login_student(client)
    client.post(f"/events/{event_id}/register", follow_redirects=True)
    client.get('/auth/logout')

    # Registrant 2
    login_student2(client)
    client.post(f"/events/{event_id}/register", follow_redirects=True)
    client.get('/auth/logout')

    # Registrant 3 (register new student)
    client.post('/auth/register', data={
        'name': 'Third Student',
        'student_id': 'STU03',
        'email': 'student3@test.edu',
        'password': 'Password@123',
        'confirm_password': 'Password@123'
    }, follow_redirects=True)
    client.post('/auth/login', data={'email': 'student3@test.edu', 'password': 'Password@123'}, follow_redirects=True)

    res3 = client.post(f"/events/{event_id}/register", follow_redirects=True)
    assert b"reached maximum capacity" in res3.data


def test_past_deadline_rejection(client, seed_data):
    """Cannot register for event with expired deadline."""
    login_student(client)
    res = client.post(f"/events/{seed_data['expired_event_id']}/register", follow_redirects=True)
    assert b"deadline for this event has passed" in res.data


def test_registration_cancellation(client, app, seed_data):
    """Student cancels booking; seat capacity is freed."""
    login_student(client)
    event_id = seed_data['event2_id']

    # Register
    client.post(f"/events/{event_id}/register", follow_redirects=True)

    # Cancel
    res_cancel = client.post(f"/events/{event_id}/cancel", follow_redirects=True)
    assert b"has been cancelled" in res_cancel.data

    with app.app_context():
        reg = EventRegistration.query.filter_by(event_id=event_id, user_id=seed_data['student_id']).first()
        assert reg.status == 'cancelled'
