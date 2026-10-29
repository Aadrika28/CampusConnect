from app.models import EventRegistration, Attendance, db
from app.utils.qr_service import generate_attendance_token, verify_attendance_token


def login_leader(client):
    client.post('/auth/login', data={'email': 'leader@test.edu', 'password': 'Password@123'}, follow_redirects=True)


def login_student(client):
    client.post('/auth/login', data={'email': 'student@test.edu', 'password': 'Password@123'}, follow_redirects=True)


def test_qr_token_crypto(app):
    """Test cryptographic token generation and tamper detection."""
    with app.app_context():
        token = generate_attendance_token(
            registration_id=10,
            event_id=5,
            user_id=2,
            registration_code="REG-TEST123456"
        )
        assert isinstance(token, str)
        assert len(token) > 20

        # Valid verification
        valid, payload = verify_attendance_token(token)
        assert valid is True
        assert payload['rid'] == 10
        assert payload['eid'] == 5
        assert payload['code'] == "REG-TEST123456"

        # Tampered token
        tampered_token = token + "xyz"
        valid_tampered, err = verify_attendance_token(tampered_token)
        assert valid_tampered is False
        assert "Invalid or tampered" in err


def test_qr_attendance_scan_workflow(client, app, seed_data):
    """Test full attendance verification scan via /api/attendance/verify."""
    event_id = seed_data['event_id']

    # 1. Student registers to obtain a pass
    login_student(client)
    client.post(f"/events/{event_id}/register", follow_redirects=True)
    client.get('/auth/logout')

    with app.app_context():
        reg = EventRegistration.query.filter_by(event_id=event_id, user_id=seed_data['student_id']).first()
        token = generate_attendance_token(reg.id, event_id, reg.user_id, reg.registration_code)

    # 2. Club leader scans pass
    login_leader(client)
    res_scan = client.post('/api/attendance/verify', json={
        'token': token,
        'event_id': event_id
    })
    assert res_scan.status_code == 200
    data = res_scan.get_json()
    assert data['success'] is True
    assert "Verified!" in data['message']
    assert data['student_name'] == "Test Student"

    # Verify DB record
    with app.app_context():
        att = Attendance.query.filter_by(registration_id=reg.id).first()
        assert att is not None
        assert att.verification_method == 'qr_scan'


def test_duplicate_attendance_rejected(client, app, seed_data):
    """Repeated scans of the same pass must be rejected with duplicate status."""
    event_id = seed_data['event_id']

    login_student(client)
    client.post(f"/events/{event_id}/register", follow_redirects=True)
    client.get('/auth/logout')

    with app.app_context():
        reg = EventRegistration.query.filter_by(event_id=event_id, user_id=seed_data['student_id']).first()
        token = generate_attendance_token(reg.id, event_id, reg.user_id, reg.registration_code)

    login_leader(client)
    # First scan
    client.post('/api/attendance/verify', json={'token': token, 'event_id': event_id})

    # Second duplicate scan
    res_dup = client.post('/api/attendance/verify', json={'token': token, 'event_id': event_id})
    assert res_dup.status_code == 409
    dup_data = res_dup.get_json()
    assert dup_data['duplicate'] is True
    assert "ALREADY marked" in dup_data['message']


def test_event_mismatch_rejection(client, app, seed_data):
    """Ticket for Event 1 presented at Event 2 must be rejected."""
    event1_id = seed_data['event_id']
    event2_id = seed_data['event2_id']

    # Register for Event 1
    login_student(client)
    client.post(f"/events/{event1_id}/register", follow_redirects=True)
    client.get('/auth/logout')

    with app.app_context():
        reg = EventRegistration.query.filter_by(event_id=event1_id, user_id=seed_data['student_id']).first()
        token = generate_attendance_token(reg.id, event1_id, reg.user_id, reg.registration_code)

    # Leader attempts to scan token under Event 2
    login_leader(client)
    res_mismatch = client.post('/api/attendance/verify', json={
        'token': token,
        'event_id': event2_id
    })
    assert res_mismatch.status_code == 400
    assert "Event Mismatch" in res_mismatch.get_json()['message']


def test_manual_code_fallback(client, app, seed_data):
    """Verify attendance using raw registration code fallback."""
    event_id = seed_data['event2_id']

    login_student(client)
    client.post(f"/events/{event_id}/register", follow_redirects=True)
    client.get('/auth/logout')

    with app.app_context():
        reg = EventRegistration.query.filter_by(event_id=event_id, user_id=seed_data['student_id']).first()
        raw_code = reg.registration_code

    login_leader(client)
    res_manual = client.post('/api/attendance/verify', json={
        'code': raw_code,
        'event_id': event_id
    })
    assert res_manual.status_code == 200
    assert res_manual.get_json()['verification_method'] == 'manual'


def test_unauthorized_scanner_rejection(client, seed_data):
    """A regular student cannot call /api/attendance/verify."""
    login_student(client)
    res = client.post('/api/attendance/verify', json={
        'code': 'REG-XYZ',
        'event_id': seed_data['event_id']
    })
    assert res.status_code == 403
