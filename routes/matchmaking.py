from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Challenge
import uuid

matchmaking_bp = Blueprint('matchmaking', __name__)

# Coda in memoria per esercizio
queue = {}  # { 'push-up': ['user_id1', ...] }

@matchmaking_bp.route('/join', methods=['POST'])
@jwt_required()
def join_queue():
    user_id = get_jwt_identity()
    data = request.get_json()
    exercise = data.get('exercise', 'push-up')
    
    # Rimuovi utente da tutte le code
    for ex in queue:
        if user_id in queue[ex]:
            queue[ex].remove(user_id)
    
    if exercise not in queue:
        queue[exercise] = []
    
    # Cerca avversario in attesa
    waiting = [uid for uid in queue[exercise] if uid != user_id]
    
    if waiting:
        opponent_id = waiting[0]
        queue[exercise].remove(opponent_id)
        
        challenge = Challenge(
            id=str(uuid.uuid4()),
            user_id=opponent_id,
            opponent_id=user_id,
            exercise=exercise,
            duration=60,
            mode='duel',
            status='active'
        )
        db.session.add(challenge)
        db.session.commit()
        
        return jsonify({
            'status': 'matched',
            'challenge': challenge.to_dict(),
            'role': 'opponent'
        }), 200
    else:
        queue[exercise].append(user_id)
        return jsonify({
            'status': 'waiting',
            'exercise': exercise,
            'position': len(queue[exercise])
        }), 200


@matchmaking_bp.route('/leave', methods=['POST'])
@jwt_required()
def leave_queue():
    user_id = get_jwt_identity()
    for ex in queue:
        if user_id in queue[ex]:
            queue[ex].remove(user_id)
    return jsonify({'status': 'left'}), 200
