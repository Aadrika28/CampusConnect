from flask import request, session
from app.models import db, AuditLog


def log_audit(action, entity_type, entity_id=None, details=None, user_id=None):
    """
    Records an administrative or critical operational action into AuditLogs.
    """
    try:
        if user_id is None:
            user_id = session.get('user_id')

        ip_address = request.remote_addr if request else '127.0.0.1'

        log_entry = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            details=details,
            ip_address=ip_address
        )
        db.session.add(log_entry)
        db.session.commit()
    except Exception:
        db.session.rollback()
