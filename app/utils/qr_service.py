import io
import base64
import qrcode
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from flask import current_app


def get_serializer():
    """Returns URLSafeTimedSerializer using app's QR secret key."""
    secret_key = current_app.config.get('QR_SECRET_KEY') or current_app.config['SECRET_KEY']
    return URLSafeTimedSerializer(secret_key, salt='campusconnect-attendance-salt')


def generate_attendance_token(registration_id, event_id, user_id, registration_code):
    """Generate cryptographically signed token containing registration identification."""
    s = get_serializer()
    payload = {
        'rid': registration_id,
        'eid': event_id,
        'uid': user_id,
        'code': registration_code
    }
    return s.dumps(payload)


def verify_attendance_token(token, max_age=86400 * 30):
    """
    Verify signed token and return decoded payload.
    Returns tuple: (is_valid, payload_or_error_message)
    """
    s = get_serializer()
    try:
        payload = s.loads(token, max_age=max_age)
        return True, payload
    except SignatureExpired:
        return False, "QR pass has expired. Please refresh your ticket."
    except BadSignature:
        return False, "Invalid or tampered QR pass signature."
    except Exception as e:
        return False, f"Verification failed: {str(e)}"


def generate_qr_base64(data_payload):
    """
    Generates a QR code image as a base64 encoded PNG string.
    Suitable for direct embedding into HTML `data:image/png;base64,...`
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=3,
    )
    qr.add_data(data_payload)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#1e293b", back_color="#ffffff")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    img_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return f"data:image/png;base64,{img_b64}"
