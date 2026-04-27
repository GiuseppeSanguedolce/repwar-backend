from flask import Flask, jsonify
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from config import Config
from models import db, bcrypt

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    db.init_app(app)
    bcrypt.init_app(app)
    JWTManager(app)
    CORS(app)
    
    from routes.auth import auth_bp
    from routes.challenges import challenges_bp
    from routes.users import users_bp
    from routes.matchmaking import matchmaking_bp
    from routes.notifications import notifications_bp
    from routes.websocket import ws_bp
    from routes.storage import storage_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(challenges_bp, url_prefix='/api/challenges')
    app.register_blueprint(users_bp, url_prefix='/api/users')
    app.register_blueprint(matchmaking_bp, url_prefix='/api/matchmaking')
    app.register_blueprint(notifications_bp, url_prefix='/api/notifications')
    app.register_blueprint(ws_bp, url_prefix='/api/ws')
    app.register_blueprint(storage_bp, url_prefix='/api/storage')
    
    @app.route('/api/health')
    def health():
        return jsonify({'status': 'ok', 'app': 'RepWar API', 'version': '2.0'})
    
    with app.app_context():
        try:
            db.create_all()
            print('✅ Database pronto')
        except Exception as e:
            print(f'✅ Database pronto (tabelle esistenti)')
    
    return app

if __name__ == '__main__':
    app = create_app()
    print('🚀 RepWar Backend su http://localhost:8080')
    app.run(debug=False, host='0.0.0.0', port=8080)
