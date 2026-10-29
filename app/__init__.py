import os
from datetime import datetime
from flask import Flask, render_template, session, send_from_directory, g
from flask_wtf.csrf import CSRFProtect
from app.models import db, User, Notification
from config import config_by_name

csrf = CSRFProtect()


def create_app(config_name=None):
    """Application factory for CampusConnect."""
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'development')

    app = Flask(__name__)
    app.config.from_object(config_by_name.get(config_name, config_by_name['default']))

    # Ensure required runtime folders exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.root_path, '..', 'instance'), exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    csrf.init_app(app)

    # Context processors to make user and utility data available in all templates
    @app.context_processor
    def inject_global_data():
        current_user = None
        unread_count = 0
        if 'user_id' in session:
            current_user = User.query.get(session['user_id'])
            if current_user:
                unread_count = current_user.unread_notifications_count()
        return {
            'current_user': current_user,
            'unread_notifications_count': unread_count,
            'now': datetime.utcnow()
        }

    # Template filters for formatting dates and badges
    @app.template_filter('format_datetime')
    def format_datetime_filter(value, fmt='%b %d, %Y - %I:%M %p'):
        if not value:
            return ''
        return value.strftime(fmt)

    @app.template_filter('format_date')
    def format_date_filter(value, fmt='%b %d, %Y'):
        if not value:
            return ''
        return value.strftime(fmt)

    # Route to serve locally uploaded files
    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    # Register blueprints
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.student import student_bp
    from app.routes.events import events_bp
    from app.routes.clubs import clubs_bp
    from app.routes.club_leader import club_leader_bp
    from app.routes.admin import admin_bp
    from app.routes.analytics import analytics_bp
    from app.routes.api import api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(student_bp, url_prefix='/student')
    app.register_blueprint(events_bp, url_prefix='/events')
    app.register_blueprint(clubs_bp, url_prefix='/clubs')
    app.register_blueprint(club_leader_bp, url_prefix='/club-leader')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(analytics_bp, url_prefix='/analytics')
    app.register_blueprint(api_bp, url_prefix='/api')

    # Error handlers
    @app.errorhandler(403)
    def forbidden(error):
        return render_template('errors/403.html', error=error), 403

    @app.errorhandler(404)
    def not_found(error):
        return render_template('errors/404.html', error=error), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        db.session.rollback()
        return render_template('errors/500.html', error=error), 500

    return app
