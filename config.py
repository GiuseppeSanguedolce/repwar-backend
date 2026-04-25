import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'repwar-secret')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'repwar-jwt')
    
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///repwar.db')
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_ACCESS_TOKEN_EXPIRES = 60 * 60 * 24 * 30  # 30 giorni
