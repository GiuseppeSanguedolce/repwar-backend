from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Challenge
import os
import requests
import uuid

storage_bp = Blueprint('storage', __name__)

SUPABASE_URL = "https://ptlzvnajxllxykcygthd.supabase.co"
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')

@storage_bp.route('/upload-url', methods=['POST'])
@jwt_required()
def get_upload_url():
    """Restituisce un URL firmato per uploadare il video direttamente da iOS"""
    user_id = get_jwt_identity()
    data = request.get_json()
    challenge_id = data.get('challenge_id', str(uuid.uuid4()))
    
    filename = f"{user_id}/{challenge_id}.mp4"
    
    # Crea signed URL per upload diretto
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json'
    }
    
    res = requests.post(
        f"{SUPABASE_URL}/storage/v1/object/sign/videos/{filename}",
        headers=headers,
        json={'expiresIn': 300}  # 5 minuti
    )
    
    if res.status_code == 200:
        signed_url = res.json().get('signedURL')
        public_url = f"{SUPABASE_URL}/storage/v1/object/public/videos/{filename}"
        return jsonify({
            'signed_url': f"{SUPABASE_URL}{signed_url}",
            'public_url': public_url,
            'filename': filename
        }), 200
    else:
        return jsonify({'error': 'Errore generazione URL'}), 500


@storage_bp.route('/save-video', methods=['POST'])
@jwt_required()
def save_video():
    """Salva l'URL del video nel database dopo l'upload"""
    user_id = get_jwt_identity()
    data = request.get_json()
    challenge_id = data.get('challenge_id')
    video_url = data.get('video_url')
    
    if not challenge_id or not video_url:
        return jsonify({'error': 'Dati mancanti'}), 400
    
    challenge = Challenge.query.get(challenge_id)
    if not challenge:
        return jsonify({'error': 'Sfida non trovata'}), 404
    
    challenge.video_url = video_url
    db.session.commit()
    
    return jsonify({'status': 'ok', 'video_url': video_url}), 200
