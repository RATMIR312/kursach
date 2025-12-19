import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
import json
from typing import Dict, List, Optional, Any
from flask import current_app
from models import db, Team, Player, Match, Innings, PlayerPerformance

class DatabaseManager:
    """Менеджер для работы с базой данных"""
    
    @staticmethod
    def init_db(app):
        """Инициализация базы данных"""
        with app.app_context():
            db.create_all()
            # Создаем тестовые данные если база пустая
            if not Team.query.first():
                DatabaseManager._create_sample_data()
    
    @staticmethod
    def _create_sample_data():
        """Создание тестовых данных"""
        print("Creating sample data...")
        
        # Создаем команды
        teams_data = [
            {'name': 'India', 'short_name': 'IND', 'country': 'India'},
            {'name': 'Australia', 'short_name': 'AUS', 'country': 'Australia'},
            {'name': 'England', 'short_name': 'ENG', 'country': 'England'},
            {'name': 'Pakistan', 'short_name': 'PAK', 'country': 'Pakistan'},
        ]
        
        teams = {}
        for team_data in teams_data:
            team = Team(**team_data)
            db.session.add(team)
            teams[team_data['short_name']] = team
        
        db.session.commit()
        
        # Создаем игроков
        players_data = [
            {'full_name': 'Virat Kohli', 'team': teams['IND'], 'role': 'batsman', 
             'batting_style': 'Right-hand bat', 'total_runs': 12898, 'total_matches': 265},
            {'full_name': 'Rohit Sharma', 'team': teams['IND'], 'role': 'batsman',
             'batting_style': 'Right-hand bat', 'total_runs': 10123, 'total_matches': 248},
            {'full_name': 'Pat Cummins', 'team': teams['AUS'], 'role': 'bowler',
             'bowling_style': 'Right-arm fast', 'total_wickets': 216, 'total_matches': 77},
            {'full_name': 'Joe Root', 'team': teams['ENG'], 'role': 'batsman',
             'batting_style': 'Right-hand bat', 'total_runs': 9278, 'total_matches': 152},
        ]
        
        for player_data in players_data:
            player = Player(**player_data)
            db.session.add(player)
        
        db.session.commit()
        
        # Создаем матч
        from datetime import datetime
        match = Match(
            match_date=datetime(2023, 10, 15, 14, 30),
            venue='Wankhede Stadium, Mumbai',
            match_type='ODI',
            tournament='ICC Cricket World Cup 2023',
            status='completed',
            team1_id=teams['IND'].id,
            team2_id=teams['AUS'].id,
            winner_id=teams['IND'].id,
            team1_score='326/5 (50 ov)',
            team2_score='289/10 (48.2 ov)',
            result='India won by 37 runs'
        )
        db.session.add(match)
        db.session.commit()
        
        print("Sample data created successfully!")
    
    @staticmethod
    def get_team_stats(team_id: int) -> Dict[str, Any]:
        """Получение статистики команды"""
        team = Team.query.get_or_404(team_id)
        
        # Статистика матчей
        matches_played = Match.query.filter(
            (Match.team1_id == team_id) | (Match.team2_id == team_id)
        ).count()
        
        matches_won = Match.query.filter_by(winner_id=team_id).count()
        matches_lost = matches_played - matches_won
        
        # Статистика игроков
        players = Player.query.filter_by(team_id=team_id).all()
        total_runs = sum(p.total_runs for p in players)
        total_wickets = sum(p.total_wickets for p in players)
        
        # Лучшие игроки
        top_batsmen = sorted(players, key=lambda x: x.total_runs, reverse=True)[:3]
        top_bowlers = sorted(players, key=lambda x: x.total_wickets, reverse=True)[:3]
        
        return {
            'team': team.to_dict(),
            'matches_played': matches_played,
            'matches_won': matches_won,
            'matches_lost': matches_lost,
            'win_percentage': round((matches_won / matches_played * 100), 2) if matches_played > 0 else 0,
            'total_runs': total_runs,
            'total_wickets': total_wickets,
            'top_batsmen': [p.to_dict() for p in top_batsmen],
            'top_bowlers': [p.to_dict() for p in top_bowlers]
        }
    
    @staticmethod
    def get_player_stats(player_id: int) -> Dict[str, Any]:
        """Получение детальной статистики игрока"""
        player = Player.query.get_or_404(player_id)
        
        performances = PlayerPerformance.query.filter_by(player_id=player_id).all()
        
        if performances:
            # Агрегированная статистика из performances
            total_performance_runs = sum(p.runs_scored for p in performances)
            total_performance_wickets = sum(p.wickets_taken for p in performances)
            total_balls_faced = sum(p.balls_faced for p in performances)
            total_overs_bowled = sum(p.overs_bowled for p in performances)
            
            # Рассчитываем средние
            batting_average = round(total_performance_runs / len([p for p in performances if p.runs_scored > 0]), 2) if any(p.runs_scored > 0 for p in performances) else 0
            bowling_average = round(total_performance_wickets / len([p for p in performances if p.wickets_taken > 0]), 2) if any(p.wickets_taken > 0 for p in performances) else 0
        else:
            total_performance_runs = 0
            total_performance_wickets = 0
            batting_average = 0
            bowling_average = 0
        
        return {
            'player': player.to_dict(),
            'performance_stats': {
                'total_performance_runs': total_performance_runs,
                'total_performance_wickets': total_performance_wickets,
                'batting_average': batting_average,
                'bowling_average': bowling_average,
                'total_performances': len(performances)
            },
            'recent_performances': [p.to_dict() for p in performances[:5]]
        }
    
    @staticmethod
    def save_scraped_data(data: Dict[str, Any]) -> bool:
        """Сохранение скрапированных данных в БД"""
        try:
            # Сохранение матчей
            for match_data in data.get('matches', []):
                match = Match.query.filter_by(scraped_match_id=match_data.get('scraped_id')).first()
                
                if not match:
                    match = Match()
                
                # Обновляем поля
                for key, value in match_data.items():
                    if hasattr(match, key):
                        setattr(match, key, value)
                
                db.session.add(match)
            
            # Сохранение игроков
            for player_data in data.get('players', []):
                player = Player.query.filter_by(scraped_id=player_data.get('scraped_id')).first()
                
                if not player:
                    player = Player()
                
                for key, value in player_data.items():
                    if hasattr(player, key):
                        setattr(player, key, value)
                
                db.session.add(player)
            
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Error saving scraped data: {e}")
            return False
    
    @staticmethod
    def get_recent_matches(limit: int = 10) -> List[Dict]:
        """Получение последних матчей"""
        matches = Match.query.order_by(Match.match_date.desc()).limit(limit).all()
        return [match.to_dict() for match in matches]
    
    @staticmethod
    def get_top_players(by: str = 'runs', limit: int = 10) -> List[Dict]:
        """Получение лучших игроков по статистике"""
        if by == 'runs':
            players = Player.query.order_by(Player.total_runs.desc()).limit(limit).all()
        elif by == 'wickets':
            players = Player.query.order_by(Player.total_wickets.desc()).limit(limit).all()
        else:
            players = Player.query.order_by(Player.total_matches.desc()).limit(limit).all()
        
        return [player.to_dict() for player in players]

@contextmanager
def get_db_connection():
    """Контекстный менеджер для соединения с БД"""
    conn = None
    try:
        conn = sqlite3.connect('instance/cricket.db')
        conn.row_factory = sqlite3.Row
        yield conn
    finally:
        if conn:
            conn.close()