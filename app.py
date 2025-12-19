from flask import Flask, render_template, request, jsonify, redirect, url_for
from models import db, Match, Player, PlayerPoints
from scraper import fetch_live_matches, scrape_real_data
from score_calculator import calculate_batting_points, calculate_bowling_points
from datetime import datetime
import traceback

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cricket.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# ==============================================
# ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ
# ==============================================

def init_sample_data():
    """Инициализация тестовых данных (аналогично addSample() в ЛР №2)"""
    try:
        if Match.query.count() > 0:
            print("База данных уже содержит данные, пропускаем инициализацию.")
            return

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
        print("✅ Тестовые данные успешно добавлены в базу.")
        
    except Exception as e:
        print(f"❌ Ошибка при инициализации данных: {e}")
        db.session.rollback()

with app.app_context():
    db.create_all()
    print("✅ Таблицы базы данных созданы/проверены.")
    init_sample_data()

# ==============================================
# ВЕБ-ИНТЕРФЕЙС (HTML СТРАНИЦЫ)
# ==============================================

@app.route('/')
def index():
    """Главная страница"""
    matches_count = Match.query.count()
    players_count = Player.query.count()
    calculations_count = PlayerPoints.query.count()
    return render_template('index.html', 
                          matches_count=matches_count,
                          players_count=players_count,
                          calculations_count=calculations_count)

@app.route('/matches')
def matches_page():
    """Страница матчей с данными из БД"""
    matches = Match.query.all()
    return render_template('matches.html', matches=matches)

@app.route('/players')
def players_page():
    """Страница игроков"""
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

# ==============================================
# API ЭНДПОИНТЫ
# ==============================================

@app.route('/api/health')
def health_check():
    """Проверка работоспособности API и БД"""
    try:
        matches = Match.query.count()
        players = Player.query.count()
        points = PlayerPoints.query.count()
        return jsonify({
            "status": "healthy",
            "service": "Cricket Score API",
            "database": "connected",
            "stats": {
                "matches": matches,
                "players": players,
                "calculations": points
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/matches', methods=['GET'])
def get_matches_api():
    """API для получения списка матчей (JSON)"""
    try:
        matches = Match.query.all()
        return jsonify([match.to_dict() for match in matches])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/players', methods=['GET'])
def get_players_api():
    """API для получения списка игроков с фильтрацией"""
    try:
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
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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

@app.route('/api/players/top/<role>')
def get_top_players(role):
    """Получение топ игроков по роли"""
    try:
        if role == 'batsman':
            players = Player.query.filter_by(role='batsman').order_by(Player.runs.desc()).limit(10).all()
        elif role == 'bowler':
            players = Player.query.filter_by(role='bowler').order_by(Player.wickets.desc()).limit(10).all()
        else:
            players = []
        
        return jsonify([player.to_dict() for player in players])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/points/history')
def get_points_history():
    """История расчетов очков"""
    try:
        history = PlayerPoints.query.order_by(PlayerPoints.calculation_date.desc()).all()
        return jsonify([record.to_dict() for record in history])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==============================================
# ВЕБ-СКРАПИНГ ЭНДПОИНТЫ
# ==============================================

@app.route('/api/scrape/matches')
def scrape_matches():
    """API эндпоинт для запуска веб-скрапинга матчей"""
    print("[DEBUG] Вызов /api/scrape/matches")
    
    try:
        matches_data = fetch_live_matches()
        
        if not matches_data or len(matches_data) == 0:
            print("[DEBUG] Нет данных от скрапинга")
            return jsonify({
                'status': 'success',
                'message': 'Скрапинг выполнен, но матчи не найдены',
                'matches_added': 0,
                'total_matches': Match.query.count()
            })
        
        print(f"[DEBUG] Получено {len(matches_data)} матчей из скрапинга")
        
        matches_added = 0
        for match_data in matches_data:
            try:
                existing_match = Match.query.filter_by(
                    team1=match_data.get('team1', ''),
                    team2=match_data.get('team2', '')
                ).first()
                
                if not existing_match:
                    new_match = Match(
                        team1=match_data.get('team1', 'Team A'),
                        team2=match_data.get('team2', 'Team B'),
                        venue=match_data.get('venue', 'Неизвестно'),
                        format=match_data.get('format', 'Неизвестно'),
                        status=match_data.get('status', 'Scheduled'),
                        score=match_data.get('score', ''),
                        match_date=datetime.utcnow()
                    )
                    
                    db.session.add(new_match)
                    matches_added += 1
                    print(f"[DEBUG] Добавлен матч: {new_match.team1} vs {new_match.team2}")
                    
            except Exception as e:
                print(f"[ERROR] Ошибка при обработке матча: {e}")
                continue
        
        db.session.commit()
        
        print(f"[DEBUG] Всего добавлено матчей: {matches_added}")
        
        return jsonify({
            'status': 'success',
            'message': f'Добавлено {matches_added} новых матчей',
            'matches_added': matches_added,
            'total_matches': Match.query.count(),
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        print(f"[ERROR] Критическая ошибка в scrape_matches: {e}")
        traceback.print_exc()
        
        return jsonify({
            'status': 'error',
            'message': f'Ошибка сервера: {str(e)}',
            'matches_added': 0,
            'error_type': type(e).__name__
        }), 500

@app.route('/api/scrape/test')
def scrape_test():
    """Тестовый эндпоинт для проверки скрапинга без сохранения в БД"""
    try:
        matches_data = fetch_live_matches()
        
        return jsonify({
            'status': 'success',
            'test_data': True,
            'matches_count': len(matches_data),
            'matches': matches_data[:3],
            'note': 'Тестовый запрос, данные не сохраняются в БД'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# ==============================================
# ЗАПУСК ПРИЛОЖЕНИЯ
# ==============================================

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
