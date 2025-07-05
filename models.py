from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class UserCredentials(db.Model):
    __tablename__ = 'user_credentials'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    api_key = db.Column(db.String(120), nullable=False)
    password = db.Column(db.String(120), nullable=False)
    webhook_secret = db.Column(db.String(120), unique=True)
    hash_value = db.Column(db.String(500))  # Login hash değerini saklamak için
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<UserCredentials {self.username}>'
