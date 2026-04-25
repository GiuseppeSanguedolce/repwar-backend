from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, User, Challenge, Notification
from datetime import datetime
import uuid

challenges_bp = Blueprint('challenges', __name__)

@challenges_bp.route('/feed', methods=['GET'])
@jwt_required()
def get_feed():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    challenges = Challenge.query\
        .filter_by(status='completed')\
        .order_by(Challenge.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'challenges': [c.to_dict() for c in challenges.items],
        'total': challenges.total,
        'pages': challenges.pages,
        'current_page': page
    }), 200


@challenges_bp.route('/', methods=['POST'])
@jwt_required()
def create_challenge():
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data.get('exercise'):
        return jsonify({'error': 'Esercizio obbligatorio'}), 400
    
    challenge = Challenge(
        id=str(uuid.uuid4()),
        user_id=user_id,
        opponent_id=data.get('opponent_id'),
        exercise=data['exercise'],
        duration=data.get('duration', 60),
        mode=data.get('mode', 'duel'),
        caption=data.get('caption', ''),
        status='pending'
    )
    db.session.add(challenge)
    
    # Notifica avversario
    if data.get('opponent_id'):
        challenger = User.query.get(user_id)
        notif = Notification(
            id=str(uuid.uuid4()),
            user_id=data['opponent_id'],
            from_user_id=user_id,
            type='challenge',
            challenge_id=challenge.id,
            message=f"@{challenger.username} ti ha sfidato a {data['exercise']} · {data.get('duration', 60)}s"
        )
        db.session.add(notif)
    
    db.session.commit()
    return jsonify({'challenge': challenge.to_dict()}), 201


@challenges_bp.route('/<challenge_id>/complete', methods=['POST'])
@jwt_required()
def complete_challenge(challenge_id):
    user_id = get_jwt_identity()
    challenge = Challenge.query.get(challenge_id)
    data = request.get_json()
    
    if not challenge:
        return jsonify({'error': 'Sfida non trovata'}), 404
    
    if user_id == challenge.user_id:
        challenge.creator_reps = data.get('reps', 0)
        challenge.creator_forma = data.get('forma', 0)
    else:
        challenge.opponent_reps = data.get('reps', 0)
        challenge.opponent_forma = data.get('forma', 0)
    
    # Completa se entrambi hanno finito
    if challenge.creator_reps > 0 and challenge.opponent_reps > 0:
        challenge.status = 'completed'
        challenge.completed_at = datetime.utcnow()
        
        if challenge.creator_reps >= challenge.opponent_reps:
            challenge.winner_id = challenge.user_id
        else:
            challenge.winner_id = challenge.opponent_id
        
        # Aggiorna stats
        creator = User.query.get(challenge.user_id)
        opponent = User.query.get(challenge.opponent_id)
        
        if creator:
            creator.total_challenges += 1
            if challenge.winner_id == creator.id:
                creator.wins += 1
                creator.points += 10
        
        if opponent:
            opponent.total_challenges += 1
            if challenge.winner_id == opponent.id:
                opponent.wins += 1
                opponent.points += 10
    
    db.session.commit()
    return jsonify({'challenge': challenge.to_dict()}), 200


@challenges_bp.route('/<challenge_id>/like', methods=['POST'])
@jwt_required()
def like_challenge(challenge_id):
    challenge = Challenge.query.get(challenge_id)
    if not challenge:
        return jsonify({'error': 'Sfida non trovata'}), 404
    challenge.likes += 1
    db.session.commit()
    return jsonify({'likes': challenge.likes}), 200


@challenges_bp.route('/<challenge_id>', methods=['GET'])
@jwt_required()
def get_challenge(challenge_id):
    challenge = Challenge.query.get(challenge_id)
    if not challenge:
        return jsonify({'error': 'Sfida non trovata'}), 404
    return jsonify({'challenge': challenge.to_dict()}), 200
