#!/usr/bin/env python3
"""
Скрипт для инициализации базы данных
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import app, db
from models import Team, Player, Match
from datetime import datetime

def init_database():
    """Инициализация базы данных с тестовыми данными"""
    with app.app_context():
        # Создаем все таблицы
        db.create_all()
        print("✅ Таблицы созданы")
        
        # Проверяем, есть ли уже данные
        if Team.query.first():
            print("⚠️  В базе уже есть данные, пропускаем создание тестовых")
            return
        
        # Создаем тестовые команды
        teams = [
            Team(name='India', short_name='IND', country='India'),
            Team(name='Australia', short_name='AUS', country='Australia'),
            Team(name='England', short_name='ENG', country='England'),
            Team(name='Pakistan', short_name='PAK', country='Pakistan'),
        ]
        
        for team in teams:
            db.session.add(team)
        
        db.session.commit()
        print("✅ Команды созданы")
        
        # Создаем тестовых игроков
        players = [
            Player(full_name='Virat Kohli', team_id=1, role='batsman', 
                  batting_style='Right-hand bat', total_runs=12898, total_matches=265),
            Player(full_name='Rohit Sharma', team_id=1, role='batsman',
                  batting_style='Right-hand bat', total_runs=10123, total_matches=248),
            Player(full_name='Pat Cummins', team_id=2, role='bowler',
                  bowling_style='Right-arm fast', total_wickets=216, total_matches=77),
            Player(full_name='Joe Root', team_id=3, role='batsman',
                  batting_style='Right-hand bat', total_runs=9278, total_matches=152),
        ]
        
        for player in players:
            db.session.add(player)
        
        db.session.commit()
        print("✅ Игроки созданы")
        
        # Создаем тестовый матч
        match = Match(
            match_date=datetime(2023, 10, 15, 14, 30),
            venue='Wankhede Stadium, Mumbai',
            match_type='ODI',
            tournament='ICC Cricket World Cup 2023',
            status='completed',
            team1_id=1,
            team2_id=2,
            winner_id=1,
            team1_score='326/5 (50 ov)',
            team2_score='289/10 (48.2 ov)',
            result='India won by 37 runs'
        )
        
        db.session.add(match)
        db.session.commit()
        print("✅ Тестовый матч создан")
        
        print("\n🎉 База данных успешно инициализирована!")
        print(f"Создано: {Team.query.count()} команд, {Player.query.count()} игроков, {Match.query.count()} матчей")

if __name__ == '__main__':
    init_database()
