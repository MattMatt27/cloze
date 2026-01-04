import os
import secrets
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix
from .extensions import db, migrate, login_manager
from .routes.auth import auth_bp
from .routes.auth import auth_blp
from .routes.conversations import conv_bp
from .routes.provider import provider_bp
from .routes.admin import admin_bp
from .routes.chat_windows import window_bp
from .routes.reports import reports_bp
from flask_smorest import Api

# Load variables from .env - use explicit path to ensure it's found
# Get the project root directory (two levels up from this file)
project_root = Path(__file__).parent.parent
env_path = project_root / '.env'
if not env_path.exists():
    print(f"WARNING: .env file not found at {env_path}")
else:
    load_dotenv(dotenv_path=env_path)
    print(f"✓ Loaded environment variables from {env_path}")

def create_app():
    app = Flask(__name__, template_folder="../templates", static_folder="../static")

    # Trust proxy headers (for Cloudflare/reverse proxy HTTPS)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    # Read from environment (with fallbacks)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", secrets.token_hex(32))
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///llm_chat.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config.update(
        API_TITLE="My API",
        API_VERSION="v1",
        OPENAPI_VERSION="3.0.3",
        OPENAPI_URL_PREFIX="/",
        OPENAPI_SWAGGER_UI_PATH="/docs",
        OPENAPI_SWAGGER_UI_URL="https://cdn.jsdelivr.net/npm/swagger-ui-dist/"
    )
    api = Api(app)

    # Init extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    # User loader
    from .models.core import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Blueprints
    api.register_blueprint(auth_blp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(conv_bp)
    app.register_blueprint(provider_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(window_bp)
    app.register_blueprint(reports_bp)

    # Start report scheduler (5-minute interval)
    from .services.report_scheduler import report_scheduler
    report_scheduler.init_app(app)
    with app.app_context():
        report_scheduler.start()

    # Initialize LLM provider clients
    from .services.llm_interface import LLMInterface
    LLMInterface.initialize_clients()

    return app
