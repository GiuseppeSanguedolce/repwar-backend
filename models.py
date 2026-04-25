from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
import uuid

db = SQLAlchemy()
bcrypt = Bcrypt()

# Tabella followers
followers = db.Table('followers',
    db.Column('follower_id', db.String(36), db.ForeignKey('users.id')),
    db.Column('followed_id', db.String(36), db.ForeignKey('users.id'))
)

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(30), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    avatar_color = db.Column(db.String(10), default='#E8572A')
    initials = db.Column(db.String(3), default='??')
    bio = db.Column(db.String(200), default='')
    location = db.Column(db.String(100), default='')
    total_challenges = db.Column(db.Integer, default=0)
    wins = db.Column(db.Integer, default=0)
    points = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    challenges = db.relationship('Challenge', backref='creator', lazy=True, foreign_keys='Challenge.user_id')
    following = db.relationship('User', secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers_list', lazy='dynamic'),
        lazy='dynamic'
    )

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'avatar_color': self.avatar_color,
            'initials': self.initials,
            'bio': self.bio,
            'location': self.location,
            'total_challenges': self.total_challenges,
            'wins': self.wins,
            'points': self.points,
            'followers_count': self.followers_list.count(),
            'following_count': self.following.count(),
            'win_rate': round((self.wins / self.total_challenges * 100) if self.total_challenges > 0 else 0),
            'created_at': self.created_at.isoformat()
        }


class Challenge(db.Model):
    __tablename__ = 'challenges'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    opponent_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    exercise = db.Column(db.String(50), nullable=False)
    duration = db.Column(db.Integer, default=60)
    mode = db.Column(db.String(20), default='duel')
    status = db.Column(db.String(20), default='pending')
    creator_reps = db.Column(db.Integer, default=0)
    creator_forma = db.Column(db.Integer, default=0)
    opponent_reps = db.Column(db.Integer, default=0)
    opponent_forma = db.Column(db.Integer, default=0)
    winner_id = db.Column(db.String(36), nullable=True)
    likes = db.Column(db.Integer, default=0)
    caption = db.Column(db.String(200), default='')
    video_url = db.Column(db.String(500), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        creator = User.query.get(self.user_id)
        return {
            'id': self.id,
            'user': creator.username if creator else '?',
            'initials': creator.initials if creator else '??',
            'avatar_color': creator.avatar_color if creator else '#888',
            'exercise': self.exercise,
            'duration': self.duration,
            'mode': self.mode,
            'status': self.status,
            'creator_reps': self.creator_reps,
            'creator_forma': self.creator_forma,
            'opponent_reps': self.opponent_reps,
            'opponent_forma': self.opponent_forma,
            'winner_id': self.winner_id,
            'likes': self.likes,
            'caption': self.caption,
            'video_url': self.video_url,
            'is_live': self.status == 'active',
            'participants': 2 if self.opponent_id else 1,
            'created_at': self.created_at.isoformat()
        }


class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    from_user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    type = db.Column(db.String(30), nullable=False)
    challenge_id = db.Column(db.String(36), nullable=True)
    message = db.Column(db.String(200), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        from_user = User.query.get(self.from_user_id) if self.from_user_id else None
        return {
            'id': self.id,
            'type': self.type,
            'from_user': from_user.username if from_user else 'RepWar',
            'initials': from_user.initials if from_user else 'RW',
            'color': from_user.avatar_color if from_user else '#E8572A',
            'message': self.message,
            'challenge_id': self.challenge_id,
            'is_read': self.is_read,
            'time': self.created_at.isoformat()
        }
