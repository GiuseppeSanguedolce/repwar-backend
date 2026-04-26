from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Challenge, User, Notification
import uuid
import time

matchmaking_bp = Blueprint('matchmaking', __name__)

# Coda in memoria
queue = {}

@matchmaking_bp.route('/join', methods=['POST'])
@jwt_required()
def join_queue():
    user_id = get_jwt_identity()
    data = request.get_json()
    exercise = data.get('exercise', 'push-up')
    duration = data.get('duration', 60)

    # Rimuovi da tutte le code
    for ex in queue:
        queue[ex] = [u for u in queue[ex] if u['user_id'] != user_id]

    if exercise not in queue:
        queue[exercise] = []

    # Pulisci vecchi
    now = time.time()
    queue[exercise] = [u for u in queue[exercise] if now - u['timestamp'] < 60]

    # Cerca avversario
    waiting = [u for u in queue[exercise] if u['user_id'] != user_id]

    if waiting:
        opponent = waiting[0]
        queue[exercise] = [u for u in queue[exercise] if u['user_id'] != opponent['user_id']]

        challenge = Challenge(
            id=str(uuid.uuid4()),
            user_id=opponent['user_id'],
            opponent_id=user_id,
            exercise=exercise,
            duration=duration,
            mode='duel',
            status='active'
        )
        db.session.add(challenge)

        challenger = User.query.get(user_id)
        opponent_user = User.query.get(opponent['user_id'])

        if challenger and opponent_user:
            db.session.add(Notification(
                id=str(uuid.uuid4()),
                user_id=opponent['user_id'],
                from_user_id=user_id,
                type='challenge',
                challenge_id=challenge.id,
                message=f"Sfida trovata! Vs @{challenger.username} a {exercise}!"
            ))
            db.session.add(Notification(
                id=str(uuid.uuid4()),
                user_id=user_id,
                from_user_id=opponent['user_id'],
                type='challenge',
                challenge_id=challenge.id,
                message=f"Sfida trovata! Vs @{opponent_user.username} a {exercise}!"
            ))

        db.session.commit()

        return jsonify({
            'status': 'matched',
            'challenge_id': challenge.id,
            'challenge': challenge.to_dict(),
            'opponent': opponent_user.to_dict() if opponent_user else None
        }), 200
    else:
        queue[exercise].append({
            'user_id': user_id,
            'timestamp': time.time(),
            'duration': duration
        })
        return jsonify({
            'status': 'waiting',
            'exercise': exercise,
            'position': len(queue[exercise])
        }), 200


@matchmaking_bp.route('/status', methods=['GET'])
@jwt_required()
def check_status():
    user_id = get_jwt_identity()
    exercise = request.args.get('exercise', 'push-up')

    challenge = Challenge.query.filter(
        Challenge.status == 'active',
        db.or_(Challenge.user_id == user_id, Challenge.opponent_id == user_id)
    ).order_by(Challenge.created_at.desc()).first()

    if challenge:
        opponent_id = challenge.opponent_id if challenge.user_id == user_id else challenge.user_id
        opponent = User.query.get(opponent_id)
        return jsonify({
            'status': 'matched',
            'challenge_id': challenge.id,
            'challenge': challenge.to_dict(),
            'opponent': opponent.to_dict() if opponent else None
        }), 200

    in_queue = exercise in queue and any(u['user_id'] == user_id for u in queue[exercise])
    return jsonify({'status': 'waiting' if in_queue else 'not_in_queue'}), 200


@matchmaking_bp.route('/leave', methods=['POST'])
@jwt_required()
def leave_queue():
    user_id = get_jwt_identity()
    for ex in queue:
        queue[ex] = [u for u in queue[ex] if u['user_id'] != user_id]
    return jsonify({'status': 'left'}), 200


@matchmaking_bp.route('/direct', methods=['POST'])
@jwt_required()
def create_direct_challenge():
    user_id = get_jwt_identity()
    data = request.get_json()
    opponent_username = data.get('opponent_username')
    exercise = data.get('exercise', 'push-up')
    duration = data.get('duration', 60)

    if not opponent_username:
        return jsonify({'error': 'Username avversario obbligatorio'}), 400

    opponent = User.query.filter_by(username=opponent_username).first()
    if not opponent:
        return jsonify({'error': 'Utente non trovato'}), 404

    challenger = User.query.get(user_id)

    challenge = Challenge(
        id=str(uuid.uuid4()),
        user_id=user_id,
        opponent_id=opponent.id,
        exercise=exercise,
        duration=duration,
        mode='duel',
        status='pending'
    )
    db.session.add(challenge)

    db.session.add(Notification(
        id=str(uuid.uuid4()),
        user_id=opponent.id,
        from_user_id=user_id,
        type='challenge',
        challenge_id=challenge.id,
        message=f"@{challenger.username} ti ha sfidato a {exercise} · {duration}s!"
    ))
    db.session.commit()

    return jsonify({
        'status': 'pending',
        'challenge_id': challenge.id,
        'challenge': challenge.to_dict()
    }), 201


@matchmaking_bp.route('/accept/<challenge_id>', methods=['POST'])
@jwt_required()
def accept_challenge(challenge_id):
    user_id = get_jwt_identity()
    challenge = Challenge.query.get(challenge_id)

    if not challenge:
        return jsonify({'error': 'Sfida non trovata'}), 404
    if challenge.opponent_id != user_id:
        return jsonify({'error': 'Non autorizzato'}), 403

    challenge.status = 'active'
    db.session.commit()

    return jsonify({
        'status': 'active',
        'challenge_id': challenge.id,
        'challenge': challenge.to_dict()
    }), 200
