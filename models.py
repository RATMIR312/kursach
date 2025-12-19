from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Match(db.Model):
    """Модель для хранения информации о матчах (соответствует вариантам заданий из ЛР №2)"""
    id = db.Column(db.Integer, primary_key=True)
    team1 = db.Column(db.String(100), nullable=False)
    team2 = db.Column(db.String(100), nullable=False)
    match_date = db.Column(db.DateTime, default=datetime.utcnow)
    venue = db.Column(db.String(200))
    format = db.Column(db.String(50))  # T20, ODI, Test
    status = db.Column(db.String(50))  # Live, Finished, Scheduled
    score = db.Column(db.String(200))
    
    # Связь с игроками (как в вариантах заданий с JOIN)
    players = db.relationship('Player', backref='match', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'team1': self.team1,
            'team2': self.team2,
            'match_date': self.match_date.isoformat() if self.match_date else None,
            'venue': self.venue,
            'format': self.format,
            'status': self.status,
            'score': self.score
        }

class Player(db.Model):
    """Модель для хранения информации об игроках"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50))  # batsman, bowler, all-rounder
    team = db.Column(db.String(100))
    match_id = db.Column(db.Integer, db.ForeignKey('match.id'))
    
    # Статистика (как в вариантах заданий с фильтрацией)
    runs = db.Column(db.Integer, default=0)
    wickets = db.Column(db.Integer, default=0)
    balls_faced = db.Column(db.Integer, default=0)
    runs_conceded = db.Column(db.Integer, default=0)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'role': self.role,
            'team': self.team,
            'runs': self.runs,
            'wickets': self.wickets,
            'balls_faced': self.balls_faced,
            'runs_conceded': self.runs_conceded
        }

class PlayerPoints(db.Model):
    """Модель для хранения расчетных очков игроков"""
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('player.id'))
    match_id = db.Column(db.Integer, db.ForeignKey('match.id'))
    points = db.Column(db.Float, nullable=False)
    calculation_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Связи
    player = db.relationship('Player', backref='points_history')
    match = db.relationship('Match', backref='points_history')
    
    def to_dict(self):
        return {
            'id': self.id,
            'player_name': self.player.name if self.player else None,
            'match_info': f"{self.match.team1} vs {self.match.team2}" if self.match else None,
            'points': self.points,
            'calculation_date': self.calculation_date.isoformat()
        }
