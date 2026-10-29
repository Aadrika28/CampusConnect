from app.models import User, db


def test_student_registration(client, app):
    """Test student registration flow with validation."""
    response = client.post('/auth/register', data={
        'name': 'New Student',
        'student_id': 'CS2026999',
        'email': 'newstudent@test.edu',
        'password': 'SecurePassword@123',
        'confirm_password': 'SecurePassword@123',
        'department': 'Computer Science',
        'batch_year': 2026,
        'phone': '1234567890'
    }, follow_redirects=True)

    assert response.status_code == 200
    with app.app_context():
        user = User.query.filter_by(email='newstudent@test.edu').first()
        assert user is not None
        assert user.name == 'New Student'
        assert user.role == 'student'
        assert user.check_password('SecurePassword@123')


def test_duplicate_registration_rejected(client, seed_data):
    """Duplicate student email or student_id should be rejected."""
    response = client.post('/auth/register', data={
        'name': 'Duplicate Person',
        'student_id': 'DUPL01',
        'email': 'student@test.edu', # Already exists in seed_data
        'password': 'Password@123',
        'confirm_password': 'Password@123'
    }, follow_redirects=True)

    assert b"An account with this email already exists" in response.data


def test_user_login_and_logout(client, seed_data):
    """Test login with correct & incorrect credentials, session setup, and logout."""
    # Bad login
    res_bad = client.post('/auth/login', data={
        'email': 'student@test.edu',
        'password': 'WrongPassword'
    }, follow_redirects=True)
    assert b"Invalid email address or password" in res_bad.data

    # Good login
    res_good = client.post('/auth/login', data={
        'email': 'student@test.edu',
        'password': 'Password@123'
    }, follow_redirects=True)
    assert res_good.status_code == 200
    assert b"Welcome back, Test Student!" in res_good.data

    # Logout
    res_logout = client.get('/auth/logout', follow_redirects=True)
    assert b"You have been logged out successfully" in res_logout.data


def test_role_based_redirects(client, seed_data):
    """Admin logs in and is directed to admin dashboard; leader to leader hub."""
    # Admin
    res_admin = client.post('/auth/login', data={
        'email': 'admin@test.edu',
        'password': 'Password@123'
    }, follow_redirects=True)
    assert b"Administrator Control Panel" in res_admin.data
    client.get('/auth/logout')

    # Club Leader
    res_leader = client.post('/auth/login', data={
        'email': 'leader@test.edu',
        'password': 'Password@123'
    }, follow_redirects=True)
    assert b"Club Organizer Hub" in res_leader.data
