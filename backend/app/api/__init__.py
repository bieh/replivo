def register_blueprints(app):
    from .auth import bp as auth_bp
    from .communities import bp as communities_bp
    from .tenants import bp as tenants_bp
    from .documents import bp as documents_bp
    from .conversations import bp as conversations_bp
    from .webhooks import bp as webhooks_bp
    from .dashboard import bp as dashboard_bp
    from .playground import bp as playground_bp
    from .citations import bp as citations_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(communities_bp, url_prefix='/api/communities')
    app.register_blueprint(tenants_bp, url_prefix='/api')
    app.register_blueprint(documents_bp, url_prefix='/api')
    app.register_blueprint(conversations_bp, url_prefix='/api/conversations')
    app.register_blueprint(webhooks_bp, url_prefix='/api/webhooks')
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
    app.register_blueprint(playground_bp, url_prefix='/api/playground')
    app.register_blueprint(citations_bp, url_prefix='/api/citations')
