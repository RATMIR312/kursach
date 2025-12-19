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

def init_sample_data():
    """Инициализация тестовых данных (аналогично addSample() в ЛР №2)"""
    try:
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
        print("Sample data initialized successfully")
        
    except Exception as e:
        print(f"Error initializing sample data: {e}")
        db.session.rollback()

# Создание таблиц при первом запуске
with app.app_context():
    db.create_all()
    # Добавление тестовых данных (как в ЛР №2)
    if Match.query.count() == 0:
        init_sample_data()

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
    points_history = PlayerPoints.query.order_by(PlayerPoints.calculation_date.desc()).limit(10).all()
    return render_template('admin.html', matches=matches, players=players, points_history=points_history)

# REST API endpoints (соответствует ЛР №4)
@app.route('/api/health')
def health_check():
    """Проверка работоспособности API"""
    return jsonify({
        "status": "healthy",
        "service": "Cricket Score API",
        "database": "SQLite",
        "tables": {
            "matches": Match.query.count(),
            "players": Player.query.count(),
            "points_history": PlayerPoints.query.count()
        }
    })

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
    min_runs = request.args.get('min_runs')
    min_wickets = request.args.get('min_wickets')
    
    query = Player.query
    
    if role:
        query = query.filter_by(role=role)
    if team:
        query = query.filter_by(team=team)
    if min_runs:
        query = query.filter(Player.runs >= int(min_runs))
    if min_wickets:
        query = query.filter(Player.wickets >= int(min_wickets))
    
    players = query.all()
    return jsonify([player.to_dict() for player in players])

@app.route('/api/calculate', methods=['POST'])
def calculate_points_api():
    """API для расчета очков с сохранением в БД"""
    try:
        data = request.json
        
        player_id = data.get('player_id')
        match_id = data.get('match_id')
        
        if not player_id:
            return jsonify({'error': 'player_id is required'}), 400
        
        player = Player.query.get(player_id)
        if not player:
            return jsonify({'error': 'Player not found'}), 404
        
        # Расчет очков в зависимости от роли
        points = 0
        if player.role == 'batsman':
            batting_data = {
                'runs': player.runs,
                'balls_faced': player.balls_faced if player.balls_faced > 0 else 1,
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
            # Для all-rounder рассчитываем и то, и другое
            batting_data = {
                'runs': player.runs,
                'balls_faced': player.balls_faced if player.balls_faced > 0 else 1,
                'fours': data.get('fours', 0),
                'sixes': data.get('sixes', 0),
                'dismissal_type': data.get('dismissal_type', 'not_out')
            }
            bowling_data = {
                'wickets': player.wickets,
                'runs_conceded': player.runs_conceded,
                'overs_bowled': data.get('overs_bowled', 4),
                'maidens': data.get('maidens', 0)
            }
            points = calculate_batting_points(batting_data) + calculate_bowling_points(bowling_data)
        
        # Сохранение в БД (как в ЛР №5)
        player_points = PlayerPoints(
            player_id=player_id,
            match_id=match_id if match_id else 1,
            points=points
        )
        
        db.session.add(player_points)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'player': player.name,
            'role': player.role,
            'points': points,
            'record_id': player_points.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# CRUD операции для админ-панели (соответствует ЛР №2, №5)
@app.route('/api/match', methods=['POST'])
def create_match():
    """Создание нового матча (CREATE)"""
    try:
        data = request.json
        match = Match(**data)
        db.session.add(match)
        db.session.commit()
        return jsonify({'status': 'success', 'match_id': match.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/match/<int:match_id>', methods=['PUT'])
def update_match(match_id):
    """Обновление матча (UPDATE)"""
    try:
        match = Match.query.get(match_id)
        if not match:
            return jsonify({'error': 'Match not found'}), 404
        
        data = request.json
        for key, value in data.items():
            if hasattr(match, key):
                setattr(match, key, value)
        
        db.session.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/match/<int:match_id>', methods=['DELETE'])
def delete_match(match_id):
    """Удаление матча (DELETE)"""
    try:
        match = Match.query.get(match_id)
        if not match:
            return jsonify({'error': 'Match not found'}), 404
        
        db.session.delete(match)
        db.session.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

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
        matches_added = 0
        for match_data in matches_data:
            # Проверяем, существует ли уже такой матч
            existing_match = Match.query.filter_by(
                team1=match_data.get('team1', ''),
                team2=match_data.get('team2', '')
            ).first()
            
            if not existing_match and match_data.get('team1') and match_data.get('team2'):
                match = Match(
                    team1=match_data.get('team1'),
                    team2=match_data.get('team2'),
                    venue=match_data.get('venue', 'Unknown'),
                    format=match_data.get('format', 'Unknown'),
                    status=match_data.get('status', 'Scheduled'),
                    score=match_data.get('score', '')
                )
                db.session.add(match)
                matches_added += 1
        
        db.session.commit()
        return jsonify({
            'status': 'success', 
            'matches_added': matches_added,
            'total_matches': Match.query.count()
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Инициализация базы данных при запуске
@app.before_first_request
def initialize_database():
    """Инициализация БД при первом запросе"""
    with app.app_context():
        db.create_all()
        if Match.query.count() == 0:
            init_sample_data()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
