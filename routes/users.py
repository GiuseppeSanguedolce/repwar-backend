from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, Challenge

users_bp = Blueprint('users', __name__)

@users_bp.route('/search', methods=['GET'])
@jwt_required()
def search_users():
    query = request.args.get('q', '')
    if len(query) < 2:
        users = User.query.order_by(User.points.desc()).limit(20).all()
    else:
        users = User.query.filter(
            User.username.ilike(f'%{query}%')
        ).limit(20).all()
    return jsonify({'users': [u.to_dict() for u in users]}), 200


@users_bp.route('/<username>', methods=['GET'])
@jwt_required()
def get_profile(username):
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'error': 'Utente non trovato'}), 404
    return jsonify({'user': user.to_dict()}), 200


@users_bp.route('/<username>/challenges', methods=['GET'])
@jwt_required()
def get_user_challenges(username):
    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'error': 'Utente non trovato'}), 404
    challenges = Challenge.query\
        .filter_by(user_id=user.id, status='completed')\
        .order_by(Challenge.created_at.desc())\
        .limit(20).all()
    return jsonify({'challenges': [c.to_dict() for c in challenges]}), 200


@users_bp.route('/<username>/follow', methods=['POST'])
@jwt_required()
def follow_user(username):
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)
    target = User.query.filter_by(username=username).first()
    
    if not target:
        return jsonify({'error': 'Utente non trovato'}), 404
    if target.id == current_user_id:
        return jsonify({'error': 'Non puoi seguire te stesso'}), 400
    
    if target in current_user.following:
        current_user.following.remove(target)
        following = False
    else:
        current_user.following.append(target)
        following = True
    
    db.session.commit()
    return jsonify({'following': following}), 200


@users_bp.route('/leaderboard', methods=['GET'])
@jwt_required()
def leaderboard():
    current_user_id = get_jwt_identity()
    users = User.query.order_by(User.points.desc()).limit(50).all()
    
    result = []
    for i, u in enumerate(users):
        data = u.to_dict()
        data['rank'] = i + 1
        result.append(data)
    
    # Trova posizione utente corrente
    all_users = User.query.order_by(User.points.desc()).all()
    my_rank = next((i + 1 for i, u in enumerate(all_users) if u.id == current_user_id), None)
    
    return jsonify({
        'leaderboard': result,
        'my_rank': my_rank
    }), 200
