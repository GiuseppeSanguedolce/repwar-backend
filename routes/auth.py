from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from models import db, User
import uuid

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    if not data.get('username') or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Tutti i campi sono obbligatori'}), 400
    
    if len(data['password']) < 6:
        return jsonify({'error': 'Password minimo 6 caratteri'}), 400
    
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username già in uso'}), 409
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email già registrata'}), 409
    
    user = User(
        id=str(uuid.uuid4()),
        username=data['username'],
        email=data['email'],
        initials=data['username'][:2].upper(),
        avatar_color=data.get('avatar_color', '#E8572A')
    )
    user.set_password(data['password'])
    
    db.session.add(user)
    db.session.commit()
    
    token = create_access_token(identity=user.id)
    return jsonify({'token': token, 'user': user.to_dict()}), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email e password obbligatori'}), 400
    
    user = User.query.filter_by(email=data['email']).first()
    
    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Email o password errati'}), 401
    
    token = create_access_token(identity=user.id)
    return jsonify({'token': token, 'user': user.to_dict()}), 200


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Utente non trovato'}), 404
    return jsonify({'user': user.to_dict()}), 200


@auth_bp.route('/me', methods=['PUT'])
@jwt_required()
def update_profile():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    data = request.get_json()
    
    if data.get('bio'): user.bio = data['bio']
    if data.get('location'): user.location = data['location']
    if data.get('avatar_color'): user.avatar_color = data['avatar_color']
    
    db.session.commit()
    return jsonify({'user': user.to_dict()}), 200
