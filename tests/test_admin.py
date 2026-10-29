from app.models import User, Club, db


def test_admin_access_control(client, seed_data):
    """Students receive 403 Forbidden on admin pages."""
    # Student login
    client.post('/auth/login', data={'email': 'student@test.edu', 'password': 'Password@123'}, follow_redirects=True)
    res = client.get('/admin/dashboard')
    assert res.status_code == 403

    client.get('/auth/logout')

    # Admin login
    client.post('/auth/login', data={'email': 'admin@test.edu', 'password': 'Password@123'}, follow_redirects=True)
    res_admin = client.get('/admin/dashboard')
    assert res_admin.status_code == 200
    assert b"Administrator Control Panel" in res_admin.data


def test_toggle_user_status(client, app, seed_data):
    """Admin can deactivate and reactivate student accounts."""
    client.post('/auth/login', data={'email': 'admin@test.edu', 'password': 'Password@123'}, follow_redirects=True)

    student_id = seed_data['student_id']

    # Deactivate student
    res = client.post(f"/admin/users/{student_id}/toggle-status", follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        u = User.query.get(student_id)
        assert u.is_active is False

    # Reactivate student
    client.post(f"/admin/users/{student_id}/toggle-status", follow_redirects=True)
    with app.app_context():
        u = User.query.get(student_id)
        assert u.is_active is True


def test_admin_lockout_protection(client, app, seed_data):
    """Platform prevents deactivating or demoting the last active administrator."""
    client.post('/auth/login', data={'email': 'admin@test.edu', 'password': 'Password@123'}, follow_redirects=True)

    admin_id = seed_data['admin_id']

    # Attempt to deactivate the only admin
    res_deact = client.post(f"/admin/users/{admin_id}/toggle-status", follow_redirects=True)
    assert b"Cannot deactivate the last active administrator" in res_deact.data

    with app.app_context():
        admin = User.query.get(admin_id)
        assert admin.is_active is True

    # Attempt to demote the only admin to student
    res_demote = client.post(f"/admin/users/{admin_id}/change-role", data={'role': 'student'}, follow_redirects=True)
    assert b"Cannot demote the last administrator" in res_demote.data

    with app.app_context():
        admin = User.query.get(admin_id)
        assert admin.role == 'admin'


def test_admin_create_club(client, app, seed_data):
    """Admin charters a new campus society."""
    client.post('/auth/login', data={'email': 'admin@test.edu', 'password': 'Password@123'}, follow_redirects=True)

    res = client.post('/admin/clubs', data={
        'name': 'Astronomy & Astrophysics Guild',
        'category': 'Technical',
        'faculty_coordinator': 'Dr. Carl Sagan',
        'leader_id': seed_data['leader_id'],
        'description': 'Exploring telescopes, space observations, and planetary physics.'
    }, follow_redirects=True)

    assert res.status_code == 200
    assert b"successfully established" in res.data

    with app.app_context():
        c = Club.query.filter_by(name='Astronomy & Astrophysics Guild').first()
        assert c is not None
        assert c.category == 'Technical'
