from flask import Flask, render_template, request, jsonify, redirect, url_for
from models import db, Match, Player, PlayerPoints
from scraper import fetch_live_matches, scrape_real_data
from score_calculator import calculate_batting_points, calculate_bowling_points
import json
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cricket.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Инициализация базы данных
db.init_app(app)

# Создание таблиц при первом запуске
with app.app_context():
    db.create_all()
    # Добавление тестовых данных (как в ЛР №2)
    if Match.query.count() == 0:
        init_sample_data()

def init_sample_data():
    """Инициализация тестовых данных (аналогично addSample() в ЛР №2)"""
    match1 = Match(
        team1="India",
        team2="Australia",
        venue="Sydney Cricket Ground",
        format="T20 International",
        status="Finished",
        score="India 175/4 (20), Australia 160/8 (20)"
    )
    
    match2 = Match(
        team1="England",
        team2="Pakistan",
        venue="Lord's Cricket Ground",
        format="Test Match",
        status="Live",
        score="England 342 & 210/5, Pakistan 295"
    )
    
    db.session.add(match1)
    db.session.add(match2)
    db.session.commit()
    
    # Добавление игроков (как в вариантах заданий)
    players_data = [
        {"name": "Virat Kohli", "role": "batsman", "team": "India", "match_id": 1, "runs": 45, "balls_faced": 32},
        {"name": "Jasprit Bumrah", "role": "bowler", "team": "India", "match_id": 1, "wickets": 2, "runs_conceded": 28},
        {"name": "David Warner", "role": "batsman", "team": "Australia", "match_id": 1, "runs": 55, "balls_faced": 38},
        {"name": "Joe Root", "role": "batsman", "team": "England", "match_id": 2, "runs": 85, "balls_faced": 120},
    ]
    
    for data in players_data:
        player = Player(**data)
        db.session.add(player)
    
    db.session.commit()

# Маршруты для веб-интерфейса
@app.route('/')
def index():
    """Главная страница (веб-интерфейс как в ЛР №4)"""
    return render_template('index.html')

@app.route('/matches')
def matches_page():
    """Страница матчей с данными из БД"""
    matches = Match.query.all()
    return render_template('matches.html', matches=matches)

@app.route('/players')
def players_page():
    """Страница игроков (аналог вариантов заданий ЛР №2)"""
    players = Player.query.all()
    return render_template('players.html', players=players)

@app.route('/calculate')
def calculate_page():
    """Страница расчета очков с формой"""
    players = Player.query.all()
    return render_template('calculate.html', players=players)

@app.route('/admin')
def admin_page():
    """Админ-панель для CRUD операций"""
    matches = Match.query.all()
    players = Player.query.all()
    return render_template('admin.html', matches=matches, players=players)

# REST API endpoints (соответствует ЛР №4)
@app.route('/api/matches', methods=['GET'])
def get_matches_api():
    """API для получения списка матчей (JSON)"""
    matches = Match.query.all()
    return jsonify([match.to_dict() for match in matches])

@app.route('/api/players', methods=['GET'])
def get_players_api():
    """API для получения списка игроков с фильтрацией (как в вариантах ЛР №2)"""
    role = request.args.get('role')
    team = request.args.get('team')
    
    query = Player.query
    
    if role:
        query = query.filter_by(role=role)
    if team:
        query = query.filter_by(team=team)
    
    players = query.all()
    return jsonify([player.to_dict() for player in players])

@app.route('/api/calculate', methods=['POST'])
def calculate_points_api():
    """API для расчета очков с сохранением в БД"""
    data = request.json
    
    try:
        player_id = data.get('player_id')
        match_id = data.get('match_id')
        
        player = Player.query.get(player_id)
        if not player:
            return jsonify({'error': 'Player not found'}), 404
        
        # Расчет очков в зависимости от роли
        if player.role == 'batsman':
            batting_data = {
                'runs': player.runs,
                'balls_faced': player.balls_faced,
                'fours': data.get('fours', 0),
                'sixes': data.get('sixes', 0),
                'dismissal_type': data.get('dismissal_type', 'not_out')
            }
            points = calculate_batting_points(batting_data)
            
        elif player.role == 'bowler':
            bowling_data = {
                'wickets': player.wickets,
                'runs_conceded': player.runs_conceded,
                'overs_bowled': data.get('overs_bowled', 4),
                'maidens': data.get('maidens', 0)
            }
            points = calculate_bowling_points(bowling_data)
        else:
            points = 0
        
        # Сохранение в БД (как в ЛР №5)
        player_points = PlayerPoints(
            player_id=player_id,
            match_id=match_id,
            points=points
        )
        
        db.session.add(player_points)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'player': player.name,
            'points': points,
            'record_id': player_points.id
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# CRUD операции для админ-панели (соответствует ЛР №2, №5)
@app.route('/api/match', methods=['POST'])
def create_match():
    """Создание нового матча (CREATE)"""
    data = request.json
    match = Match(**data)
    db.session.add(match)
    db.session.commit()
    return jsonify({'status': 'success', 'match_id': match.id})

@app.route('/api/match/<int:match_id>', methods=['PUT'])
def update_match(match_id):
    """Обновление матча (UPDATE)"""
    match = Match.query.get(match_id)
    if not match:
        return jsonify({'error': 'Match not found'}), 404
    
    data = request.json
    for key, value in data.items():
        setattr(match, key, value)
    
    db.session.commit()
    return jsonify({'status': 'success'})

@app.route('/api/match/<int:match_id>', methods=['DELETE'])
def delete_match(match_id):
    """Удаление матча (DELETE)"""
    match = Match.query.get(match_id)
    if not match:
        return jsonify({'error': 'Match not found'}), 404
    
    db.session.delete(match)
    db.session.commit()
    return jsonify({'status': 'success'})

# Специальные запросы (как в вариантах заданий ЛР №2)
@app.route('/api/players/top/<role>')
def get_top_players(role):
    """Получение топ игроков по роли (аналог вариантов заданий)"""
    if role == 'batsman':
        players = Player.query.filter_by(role='batsman').order_by(Player.runs.desc()).limit(10).all()
    elif role == 'bowler':
        players = Player.query.filter_by(role='bowler').order_by(Player.wickets.desc()).limit(10).all()
    else:
        players = []
    
    return jsonify([player.to_dict() for player in players])

@app.route('/api/points/history')
def get_points_history():
    """История расчетов очков (аналог вариантов заданий)"""
    history = PlayerPoints.query.order_by(PlayerPoints.calculation_date.desc()).all()
    return jsonify([record.to_dict() for record in history])

# Веб-скрапинг эндпоинт
@app.route('/api/scrape/matches')
def scrape_matches():
    """Эндпоинт для запуска веб-скрапинга"""
    try:
        matches_data = fetch_live_matches()
        
        # Сохранение в БД
        for match_data in matches_data:
            match = Match.query.filter_by(
                team1=match_data.get('team1'),
                team2=match_data.get('team2'),
                match_date=match_data.get('date')
            ).first()
            
            if not match:
                match = Match(**match_data)
                db.session.add(match)
        
        db.session.commit()
        return jsonify({'status': 'success', 'matches_added': len(matches_data)})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
