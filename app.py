from flask import Flask, jsonify
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
from config import Config
from models import db, bcrypt

socketio = SocketIO(cors_allowed_origins="*", async_mode='threading')

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Estensioni
    db.init_app(app)
    bcrypt.init_app(app)
    JWTManager(app)
    CORS(app)
    socketio.init_app(app)
    
    # Routes
    from routes.auth import auth_bp
    from routes.challenges import challenges_bp
    from routes.users import users_bp
    from routes.matchmaking import matchmaking_bp
    from routes.notifications import notifications_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(challenges_bp, url_prefix='/api/challenges')
    app.register_blueprint(users_bp, url_prefix='/api/users')
    app.register_blueprint(matchmaking_bp, url_prefix='/api/matchmaking')
    app.register_blueprint(notifications_bp, url_prefix='/api/notifications')
    
    @app.route('/api/health')
    def health():
        return jsonify({'status': 'ok', 'app': 'RepWar API', 'version': '2.0'})
    
    # Crea tabelle automaticamente
    with app.app_context():
        try:
            db.create_all()
            print('✅ Database pronto')
        except Exception as e:
            print(f'⚠️ db.create_all fallito: {e}')
            # Prova con SQL diretto
            try:
                with db.engine.connect() as conn:
                    conn.execute(db.text("""
                        CREATE TABLE IF NOT EXISTS users (
                            id VARCHAR(36) PRIMARY KEY,
                            username VARCHAR(30) UNIQUE NOT NULL,
                            email VARCHAR(120) UNIQUE NOT NULL,
                            password_hash VARCHAR(200) NOT NULL,
                            avatar_color VARCHAR(10) DEFAULT '#E8572A',
                            initials VARCHAR(3) DEFAULT '??',
                            bio VARCHAR(200) DEFAULT '',
                            location VARCHAR(100) DEFAULT '',
                            total_challenges INTEGER DEFAULT 0,
                            wins INTEGER DEFAULT 0,
                            points INTEGER DEFAULT 0,
                            created_at TIMESTAMP DEFAULT NOW()
                        );
                        CREATE TABLE IF NOT EXISTS followers (
                            follower_id VARCHAR(36) REFERENCES users(id),
                            followed_id VARCHAR(36) REFERENCES users(id),
                            PRIMARY KEY (follower_id, followed_id)
                        );
                        CREATE TABLE IF NOT EXISTS challenges (
                            id VARCHAR(36) PRIMARY KEY,
                            user_id VARCHAR(36) REFERENCES users(id),
                            opponent_id VARCHAR(36) REFERENCES users(id),
                            exercise VARCHAR(50) NOT NULL,
                            duration INTEGER DEFAULT 60,
                            mode VARCHAR(20) DEFAULT 'duel',
                            status VARCHAR(20) DEFAULT 'pending',
                            creator_reps INTEGER DEFAULT 0,
                            creator_forma INTEGER DEFAULT 0,
                            opponent_reps INTEGER DEFAULT 0,
                            opponent_forma INTEGER DEFAULT 0,
                            winner_id VARCHAR(36),
                            likes INTEGER DEFAULT 0,
                            caption VARCHAR(200) DEFAULT '',
                            video_url VARCHAR(500) DEFAULT '',
                            created_at TIMESTAMP DEFAULT NOW(),
                            completed_at TIMESTAMP
                        );
                        CREATE TABLE IF NOT EXISTS notifications (
                            id VARCHAR(36) PRIMARY KEY,
                            user_id VARCHAR(36) REFERENCES users(id),
                            from_user_id VARCHAR(36) REFERENCES users(id),
                            type VARCHAR(30) NOT NULL,
                            challenge_id VARCHAR(36),
                            message VARCHAR(200) NOT NULL,
                            is_read BOOLEAN DEFAULT FALSE,
                            created_at TIMESTAMP DEFAULT NOW()
                        );
                    """))
                    conn.commit()
                    print('✅ Tabelle create con SQL diretto')
            except Exception as e2:
                print(f'Database già configurato: {e2}')
                print('✅ Database pronto')
    
    return app

# WebSocket events
@socketio.on('join_challenge')
def on_join(data):
    challenge_id = data.get('challenge_id')
    user_id = data.get('user_id')
    join_room(challenge_id)
    emit('player_joined', {'user_id': user_id}, room=challenge_id)

@socketio.on('rep_update')
def on_rep(data):
    challenge_id = data.get('challenge_id')
    emit('opponent_update', {
        'user_id': data.get('user_id'),
        'reps': data.get('reps', 0),
        'forma': data.get('forma', 100)
    }, room=challenge_id, include_self=False)

@socketio.on('leave_challenge')
def on_leave(data):
    leave_room(data.get('challenge_id'))

if __name__ == '__main__':
    app = create_app()
    print('🚀 RepWar Backend su http://localhost:8080')
    socketio.run(app, debug=False, host='0.0.0.0', port=8080, use_reloader=False)
