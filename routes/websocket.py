from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Challenge
import time

ws_bp = Blueprint('ws', __name__)

# Store in memoria per i rep live
# { challenge_id: { user_id: { reps, forma, timestamp } } }
live_state = {}

@ws_bp.route('/update', methods=['POST'])
@jwt_required()
def update_reps():
    """iPhone manda i propri rep ogni secondo"""
    user_id = get_jwt_identity()
    data = request.get_json()
    challenge_id = data.get('challenge_id')
    reps = data.get('reps', 0)
    forma = data.get('forma', 100)

    if not challenge_id:
        return jsonify({'error': 'challenge_id obbligatorio'}), 400

    if challenge_id not in live_state:
        live_state[challenge_id] = {}

    live_state[challenge_id][user_id] = {
        'reps': reps,
        'forma': forma,
        'timestamp': time.time()
    }

    # Pulisci stati vecchi (>5 minuti)
    now = time.time()
    for cid in list(live_state.keys()):
        for uid in list(live_state[cid].keys()):
            if now - live_state[cid][uid]['timestamp'] > 300:
                del live_state[cid][uid]

    return jsonify({'status': 'ok'}), 200


@ws_bp.route('/state/<challenge_id>', methods=['GET'])
@jwt_required()
def get_state(challenge_id):
    """iPhone chiede lo stato dell'avversario"""
    user_id = get_jwt_identity()

    if challenge_id not in live_state:
        return jsonify({'players': {}}), 200

    # Restituisce lo stato di tutti tranne il richiedente
    state = live_state.get(challenge_id, {})
    opponent_state = {
        uid: data for uid, data in state.items()
        if uid != user_id
    }

    return jsonify({'players': opponent_state}), 200


@ws_bp.route('/finish', methods=['POST'])
@jwt_required()
def finish_challenge():
    """Salva il risultato finale e aggiorna Supabase"""
    user_id = get_jwt_identity()
    data = request.get_json()
    challenge_id = data.get('challenge_id')
    reps = data.get('reps', 0)
    forma = data.get('forma', 0)

    if not challenge_id:
        return jsonify({'error': 'challenge_id obbligatorio'}), 400

    challenge = Challenge.query.get(challenge_id)
    if not challenge:
        return jsonify({'error': 'Sfida non trovata'}), 404

    # Aggiorna i rep del giocatore
    if challenge.user_id == user_id:
        challenge.creator_reps = reps
        challenge.creator_forma = forma
    elif challenge.opponent_id == user_id:
        challenge.opponent_reps = reps
        challenge.opponent_forma = forma

    # Se entrambi hanno finito, determina il vincitore
    if challenge.creator_reps > 0 and challenge.opponent_reps > 0:
        from datetime import datetime
        challenge.status = 'completed'
        challenge.completed_at = datetime.utcnow()

        if challenge.creator_reps >= challenge.opponent_reps:
            challenge.winner_id = challenge.user_id
        else:
            challenge.winner_id = challenge.opponent_id

        # Aggiorna punti
        from models import User
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

    # Pulisci stato live
    if challenge_id in live_state:
        del live_state[challenge_id]

    return jsonify({
        'status': 'completed' if challenge.status == 'completed' else 'waiting',
        'challenge': challenge.to_dict()
    }), 200
