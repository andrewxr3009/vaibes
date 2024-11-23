import os

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'a3n0d0r4e0w9')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'postgresql://postgres.txyhqnbmlpcywyapxypm:futuroheine2024@aws-0-us-west-1.pooler.supabase.com:6543/postgres')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')  # URL do Redis
    CORS_HEADERS = 'Content-Type'
