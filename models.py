from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import validates

db = SQLAlchemy()

class Team(db.Model):
    """Модель команды"""
    __tablename__ = 'teams'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    short_name = db.Column(db.String(10))
    country = db.Column(db.String(50))
    founded_year = db.Column(db.Integer)
    logo_url = db.Column(db.String(500))
    
    # Связи
    players = db.relationship('Player', backref='team', lazy=True)
    matches_as_team1 = db.relationship('Match', foreign_keys='Match.team1_id', backref='team1', lazy=True)
    matches_as_team2 = db.relationship('Match', foreign_keys='Match.team2_id', backref='team2', lazy=True)
    matches_won = db.relationship('Match', foreign_keys='Match.winner_id', backref='winner', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'short_name': self.short_name,
            'country': self.country,
            'founded_year': self.founded_year,
            'total_players': len(self.players) if self.players else 0
        }

class Player(db.Model):
    """Модель игрока"""
    __tablename__ = 'players'
    
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    date_of_birth = db.Column(db.Date)
    batting_style = db.Column(db.String(50))
    bowling_style = db.Column(db.String(50))
    role = db.Column(db.String(50))  # batsman, bowler, all-rounder, wicket-keeper
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'))
    image_url = db.Column(db.String(500))
    scraped_id = db.Column(db.String(50), unique=True)  # ID из источника данных
    
    # Статистика (можно обновлять при каждом скрапинге)
    total_runs = db.Column(db.Integer, default=0)
    total_wickets = db.Column(db.Integer, default=0)
    total_matches = db.Column(db.Integer, default=0)
    highest_score = db.Column(db.Integer, default=0)
    best_bowling = db.Column(db.String(20))  # формата "5/20"
    
    # Связи
    performances = db.relationship('PlayerPerformance', backref='player', lazy=True)
    
    @validates('role')
    def validate_role(self, key, role):
        roles = ['batsman', 'bowler', 'all-rounder', 'wicket-keeper']
        if role not in roles:
            raise ValueError(f'Role must be one of {roles}')
        return role
    
    def to_dict(self):
        return {
            'id': self.id,
            'full_name': self.full_name,
            'date_of_birth': str(self.date_of_birth) if self.date_of_birth else None,
            'batting_style': self.batting_style,
            'bowling_style': self.bowling_style,
            'role': self.role,
            'team': self.team.name if self.team else None,
            'total_runs': self.total_runs,
            'total_wickets': self.total_wickets,
            'total_matches': self.total_matches,
            'highest_score': self.highest_score,
            'best_bowling': self.best_bowling
        }

class Match(db.Model):
    """Модель матча"""
    __tablename__ = 'matches'
    
    id = db.Column(db.Integer, primary_key=True)
    match_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    venue = db.Column(db.String(200))
    match_type = db.Column(db.String(50))  # T20, ODI, Test
    tournament = db.Column(db.String(100))
    status = db.Column(db.String(50))  # scheduled, live, completed, cancelled
    
    # Команды
    team1_id = db.Column(db.Integer, db.ForeignKey('teams.id'))
    team2_id = db.Column(db.Integer, db.ForeignKey('teams.id'))
    winner_id = db.Column(db.Integer, db.ForeignKey('teams.id'))
    
    # Счет
    team1_score = db.Column(db.String(50))
    team2_score = db.Column(db.String(50))
    team1_overs = db.Column(db.Float)
    team2_overs = db.Column(db.Float)
    result = db.Column(db.String(200))
    
    # Внешний ID для отслеживания
    scraped_match_id = db.Column(db.String(50), unique=True)
    
    # Связи
    innings = db.relationship('Innings', backref='match', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'match_date': self.match_date.isoformat() if self.match_date else None,
            'venue': self.venue,
            'match_type': self.match_type,
            'tournament': self.tournament,
            'status': self.status,
            'team1': self.team1.name if self.team1 else None,
            'team2': self.team2.name if self.team2 else None,
            'winner': self.winner.name if self.winner else None,
            'team1_score': self.team1_score,
            'team2_score': self.team2_score,
            'result': self.result
        }

class Innings(db.Model):
    """Модель иннингов (партии)"""
    __tablename__ = 'innings'
    
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'))
    innings_number = db.Column(db.Integer)  # 1 или 2
    batting_team_id = db.Column(db.Integer, db.ForeignKey('teams.id'))
    bowling_team_id = db.Column(db.Integer, db.ForeignKey('teams.id'))
    
    # Статистика иннингов
    total_runs = db.Column(db.Integer, default=0)
    wickets = db.Column(db.Integer, default=0)
    overs = db.Column(db.Float, default=0.0)
    extras = db.Column(db.Integer, default=0)
    
    # Связи
    batting_team = db.relationship('Team', foreign_keys=[batting_team_id])
    bowling_team = db.relationship('Team', foreign_keys=[bowling_team_id])
    performances = db.relationship('PlayerPerformance', backref='innings', lazy=True)

class PlayerPerformance(db.Model):
    """Модель выступления игрока в конкретном иннинге"""
    __tablename__ = 'player_performances'
    
    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'))
    innings_id = db.Column(db.Integer, db.ForeignKey('innings.id'))
    
    # Бэттинг статистика
    runs_scored = db.Column(db.Integer, default=0)
    balls_faced = db.Column(db.Integer, default=0)
    fours = db.Column(db.Integer, default=0)
    sixes = db.Column(db.Integer, default=0)
    strike_rate = db.Column(db.Float)
    is_out = db.Column(db.Boolean, default=False)
    dismissal_type = db.Column(db.String(50))
    
    # Боулинг статистика
    overs_bowled = db.Column(db.Float, default=0.0)
    maidens = db.Column(db.Integer, default=0)
    runs_given = db.Column(db.Integer, default=0)
    wickets_taken = db.Column(db.Integer, default=0)
    economy_rate = db.Column(db.Float)
    wide_balls = db.Column(db.Integer, default=0)
    no_balls = db.Column(db.Integer, default=0)
    
    # Полевая статистика
    catches = db.Column(db.Integer, default=0)
    stumpings = db.Column(db.Integer, default=0)
    run_outs = db.Column(db.Integer, default=0)
    
    def to_dict(self):
        return {
            'player_id': self.player_id,
            'player_name': self.player.full_name if self.player else None,
            'runs_scored': self.runs_scored,
            'balls_faced': self.balls_faced,
            'fours': self.fours,
            'sixes': self.sixes,
            'strike_rate': self.strike_rate,
            'wickets_taken': self.wickets_taken,
            'economy_rate': self.economy_rate
        }