"""
app.py - Упрощенный Cricket Scores API
"""
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from flask_apscheduler import APScheduler
from datetime import datetime, timedelta
import atexit
import os
import sys
import threading

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config
from models import db, Team, Player, Match
from database import DatabaseManager
from scraper import scraper

# Инициализация
app = Flask(__name__)
app.config.from_object(Config)
CORS(app)
db.init_app(app)

# Планировщик
scheduler = APScheduler()
scheduler.init_app(app)

# Глобальные переменные
last_update = None
is_scraping = False

# ========== СКРАПИНГ ==========

def scrape_background():
    """Фоновая задача скрапинга"""
    global is_scraping, last_update
    
    if is_scraping:
        return False
    
    is_scraping = True
    
    try:
        print("🔄 Запуск скрапинга...")
        
        with app.app_context():
            # Получаем данные
            data = scraper.scrape_all_data()
            
            # Команды
            team_map = {}
            for team in Team.query.all():
                team_map[team.name] = team.id
            
            for team_data in data['teams']:
                if team_data['name'] not in team_map:
                    new_team = Team(
                        name=team_data['name'],
                        short_name=team_data['short_name'],
                        country=team_data['country'],
                        founded_year=team_data.get('founded_year')
                    )
                    db.session.add(new_team)
                    db.session.flush()
                    team_map[team_data['name']] = new_team.id
            
            db.session.commit()
            
            # Игроки
            for player_data in data['players']:
                existing = Player.query.filter_by(scraped_id=player_data['scraped_id']).first()
                team_id = team_map.get(player_data['team_name'])
                
                if not team_id:
                    continue
                
                if existing:
                    existing.full_name = player_data['full_name']
                    existing.team_id = team_id
                    existing.total_runs = player_data['total_runs']
                    existing.total_wickets = player_data['total_wickets']
                else:
                    new_player = Player(
                        scraped_id=player_data['scraped_id'],
                        full_name=player_data['full_name'],
                        team_id=team_id,
                        total_runs=player_data['total_runs'],
                        total_wickets=player_data['total_wickets'],
                        total_matches=player_data['total_matches']
                    )
                    db.session.add(new_player)
            
            db.session.commit()
            
            # Матчи
            for match_data in data['matches']:
                existing = Match.query.filter_by(scraped_match_id=match_data['scraped_match_id']).first()
                team1_id = team_map.get(match_data['team1_name'])
                team2_id = team_map.get(match_data['team2_name'])
                
                if not team1_id or not team2_id:
                    continue
                
                if existing:
                    existing.match_date = match_data.get('match_date', datetime.now())
                    existing.status = match_data.get('status', 'scheduled')
                    existing.team1_score = match_data.get('team1_score')
                    existing.team2_score = match_data.get('team2_score')
                else:
                    new_match = Match(
                        scraped_match_id=match_data['scraped_match_id'],
                        match_date=match_data.get('match_date', datetime.now()),
                        venue=match_data.get('venue', 'Unknown'),
                        match_type=match_data.get('match_type', 'ODI'),
                        tournament=match_data.get('tournament', ''),
                        status=match_data.get('status', 'scheduled'),
                        team1_id=team1_id,
                        team2_id=team2_id,
                        team1_score=match_data.get('team1_score'),
                        team2_score=match_data.get('team2_score'),
                        result=match_data.get('result', '')
                    )
                    db.session.add(new_match)
            
            db.session.commit()
            
            # Автоматическое завершение старых матчей
            live_matches = Match.query.filter_by(status='live').all()
            for match in live_matches:
                if match.match_date and (datetime.utcnow() - match.match_date) > timedelta(hours=8):
                    match.status = 'completed'
            
            db.session.commit()
            
            last_update = datetime.now()
            print(f"✅ Скрапинг завершен: {len(data['matches'])} матчей")
            return True
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        db.session.rollback()
        return False
    finally:
        is_scraping = False

def start_scraping():
    """Запуск скрапинга в фоне"""
    thread = threading.Thread(target=scrape_background)
    thread.daemon = True
    thread.start()
    return True

# ========== API ЭНДПОИНТЫ ==========

@app.route('/api/v1/health', methods=['GET'])
def health():
    """Проверка здоровья"""
    return jsonify({
        'status': 'ok',
        'time': datetime.utcnow().isoformat(),
        'last_update': last_update.isoformat() if last_update else None,
        'scraping': is_scraping
    })

@app.route('/api/v1/matches', methods=['GET'])
def get_matches():
    """Получить матчи"""
    status = request.args.get('status')
    limit = request.args.get('limit', type=int)
    
    query = Match.query
    
    if status:
        query = query.filter_by(status=status)
    
    matches = query.order_by(Match.match_date.desc()).limit(limit or 50).all()
    
    return jsonify({
        'matches': [m.to_dict() for m in matches],
        'count': len(matches)
    })

@app.route('/api/v1/matches/<int:match_id>', methods=['GET'])
def get_match(match_id):
    """Получить матч по ID"""
    match = Match.query.get_or_404(match_id)
    return jsonify(match.to_dict())

@app.route('/api/v1/teams', methods=['GET'])
def get_teams():
    """Получить команды"""
    teams = Team.query.all()
    return jsonify({
        'teams': [t.to_dict() for t in teams],
        'count': len(teams)
    })

@app.route('/api/v1/teams/<int:team_id>', methods=['GET'])
def get_team(team_id):
    """Получить команду по ID"""
    stats = DatabaseManager.get_team_stats(team_id)
    return jsonify(stats)

@app.route('/api/v1/players', methods=['GET'])
def get_players():
    """Получить игроков"""
    team_id = request.args.get('team_id', type=int)
    limit = request.args.get('limit', type=int)
    
    query = Player.query
    
    if team_id:
        query = query.filter_by(team_id=team_id)
    
    players = query.order_by(Player.full_name).limit(limit or 50).all()
    
    return jsonify({
        'players': [p.to_dict() for p in players],
        'count': len(players)
    })

@app.route('/api/v1/players/<int:player_id>', methods=['GET'])
def get_player(player_id):
    """Получить игрока по ID"""
    stats = DatabaseManager.get_player_stats(player_id)
    return jsonify(stats)

@app.route('/api/v1/admin/update', methods=['POST'])
def update_data():
    """Ручной запуск обновления"""
    if is_scraping:
        return jsonify({'error': 'Скрапинг уже выполняется'}), 400
    
    success = start_scraping()
    
    return jsonify({
        'success': success,
        'message': 'Скрапинг запущен' if success else 'Ошибка запуска'
    })

@app.route('/api/v1/admin/status', methods=['GET'])
def get_status():
    """Статус системы"""
    return jsonify({
        'scraping': is_scraping,
        'last_update': last_update.isoformat() if last_update else None,
        'teams_count': Team.query.count(),
        'players_count': Player.query.count(),
        'matches_count': Match.query.count()
    })

# ========== ВЕБ-ИНТЕРФЕЙС ==========

@app.route('/')
def index():
    """Главная страница"""
    matches = Match.query.order_by(Match.match_date.desc()).limit(5).all()
    batsmen = Player.query.order_by(Player.total_runs.desc()).limit(5).all()
    bowlers = Player.query.order_by(Player.total_wickets.desc()).limit(5).all()
    
    return render_template('index.html',
                         matches=[m.to_dict() for m in matches],
                         batsmen=[p.to_dict() for p in batsmen],
                         bowlers=[p.to_dict() for p in bowlers],
                         last_update=last_update)

@app.route('/matches')
def matches_page():
    """Страница матчей"""
    page = request.args.get('page', 1, type=int)
    matches = Match.query.order_by(Match.match_date.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('matches.html', matches=matches, last_update=last_update)

@app.route('/players')
def players_page():
    """Страница игроков"""
    page = request.args.get('page', 1, type=int)
    players = Player.query.order_by(Player.full_name).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('players.html', players=players, last_update=last_update)

@app.route('/teams')
def teams_page():
    """Страница команд"""
    teams = Team.query.all()
    return render_template('teams.html', teams=teams, last_update=last_update)

@app.route('/admin')
def admin_page():
    """Админ-панель"""
    stats = {
        'teams': Team.query.count(),
        'players': Player.query.count(),
        'matches': Match.query.count(),
        'live': Match.query.filter_by(status='live').count()
    }
    return render_template('admin.html', stats=stats, last_update=last_update, is_scraping=is_scraping)

# ========== ПЛАНИРОВЩИК ==========

@scheduler.task('interval', id='auto_update', hours=6)
def auto_update():
    """Автоматическое обновление каждые 6 часов"""
    print(f"⏰ Автообновление: {datetime.now()}")
    start_scraping()

@scheduler.task('interval', id='hourly_check', hours=1)
def hourly_check():
    """Ежечасная проверка"""
    try:
        with app.app_context():
            live_matches = Match.query.filter_by(status='live').all()
            for match in live_matches:
                if match.match_date and (datetime.utcnow() - match.match_date) > timedelta(hours=8):
                    match.status = 'completed'
                    db.session.commit()
                    print(f"📅 Матч {match.id} завершен")
    except Exception as e:
        print(f"⚠️ Ошибка проверки: {e}")

# ========== ИНИЦИАЛИЗАЦИЯ ==========

def init_app():
    """Инициализация приложения"""
    with app.app_context():
        # Создаем таблицы
        db.create_all()
        print("✅ База данных создана")
        
        # Тестовые данные если пусто
        if not Team.query.first():
            DatabaseManager._create_sample_data()
            print("✅ Тестовые данные созданы")
        
        # Запускаем первый скрапинг
        global last_update
        start_scraping()
        last_update = datetime.now()

def shutdown():
    """Завершение работы"""
    if scheduler.running:
        scheduler.shutdown()
        print("🛑 Планировщик остановлен")

atexit.register(shutdown)

# ========== ЗАПУСК ==========

if __name__ == '__main__':
    # Инициализация
    init_app()
    
    # Планировщик
    if not scheduler.running:
        scheduler.start()
        print("✅ Планировщик запущен")
    
    print("=" * 50)
    print("🏏 Cricket Scores API")
    print("=" * 50)
    print(f"📍 http://localhost:5000")
    print(f"📊 API: http://localhost:5000/api/v1")
    print(f"🔄 Автообновление: каждые 6 часов")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
else:
    # Для Gunicorn
    init_app()
    if not scheduler.running:
        scheduler.start()
