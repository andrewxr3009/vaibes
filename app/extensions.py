from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_socketio import SocketIO
from firebase_admin import credentials, initialize_app
from google.cloud import storage
import redis
import os
from supabase import create_client

# Inicialização do SQLAlchemy
app = Flask(__name__)
db = SQLAlchemy()

# Configuração do Firebase
cred = credentials.Certificate("serviceAccountKey.json")
initialize_app(cred, {
    'storageBucket': 'app-vaibes.appspot.com'  # Seu bucket do Firebase Storage
})

# Configuração do Firebase Storage
storage_client = storage.Client.from_service_account_json("serviceAccountKey.json")
bucket_name = "app-vaibes.appspot.com"  # Seu bucket
firebase_bucket = storage_client.bucket(bucket_name)

# Configuração do Supabase com suas credenciais
supabase_url = "https://txyhqnbmlpcywyapxypm.supabase.co"  # URL do seu Supabase
supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR4eWhxbmJtbHBjeXd5YXB4eXBtIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTcyNTgxNzMyNiwiZXhwIjoyMDQxMzkzMzI2fQ.qZs74A3I1HXo6cMNxtUnJs427BLfvFhAi1-JgPLWB10"  # Chave de API do seu Supabase
supabase_client = create_client(supabase_url, supabase_key)

# Configuração do Redis
redis_client = redis.StrictRedis(host='localhost', port=6379, decode_responses=True)

# Configuração do PostgreSQL usando psycopg2
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres.txyhqnbmlpcywyapxypm:futuroheine2024@aws-0-us-west-1.pooler.supabase.com:6543/postgres'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializa extensões
cors = CORS()
socketio = SocketIO()

