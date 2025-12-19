from flask import Flask, render_template, jsonify, request, redirect, url_for, session
from flask_cors import CORS
import json
from datetime import datetime
from functools import wraps
from typing import Dict, Any

from config import Config
from models import db, Team, Player, Match, Innings, PlayerPerformance
from database import DatabaseManager, get_db_connection
from scraper import ScrapingManager

# Инициализация приложения
app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

# Инициализация базы данных
db.init_app(app)
with app.app_context():
    DatabaseManager.init_db(app)

# Инициализация менеджера скрапинга
scraping_manager = ScrapingManager(Config)

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

def admin_required(f):
    """Декоратор для проверки админских прав"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth = request.authorization
        if not auth or auth.username != Config.ADMIN_USERNAME or auth.password != Config.ADMIN_PASSWORD:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

def paginate_query(query, page, per_page):
    """Пагинация запроса"""
    return query.paginate(page=page, per_page=per_page, error_out=False)

# ========== API ЭНДПОИНТЫ ==========

@app.route(f'{Config.API_PREFIX}/health', methods=['GET'])
def health_check():
    """Проверка здоровья API"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    })

# --- Матчи ---

@app.route(f'{Config.API_PREFIX}/matches', methods=['GET'])
def get_matches():
    """Получение списка матчей"""
    page = request.args.get('page', 1, type=int)
    match_type = request.args.get('type')
    status = request.args.get('status')
    team_id = request.args.get('team_id', type=int)
    
    query = Match.query
    
    if match_type:
        query = query.filter_by(match_type=match_type)
    if status:
        query = query.filter_by(status=status)
    if team_id:
        query = query.filter((Match.team1_id == team_id) | (Match.team2_id == team_id))
    
    matches = query.order_by(Match.match_date.desc()).all()
    
    return jsonify({
        'matches': [match.to_dict() for match in matches],
        'total': len(matches)
    })

@app.route(f'{Config.API_PREFIX}/matches/<int:match_id>', methods=['GET'])
def get_match(match_id):
    """Получение информации о конкретном матче"""
    match = Match.query.get_or_404(match_id)
    
    # Получаем информацию об иннингах
    innings = Innings.query.filter_by(match_id=match_id).all()
    innings_data = []
    
    for inning in innings:
        performances = PlayerPerformance.query.filter_by(innings_id=inning.id).all()
        innings_data.append({
            'innings_number': inning.innings_number,
            'batting_team': inning.batting_team.name if inning.batting_team else None,
            'bowling_team': inning.bowling_team.name if inning.bowling_team else None,
            'total_runs': inning.total_runs,
            'wickets': inning.wickets,
            'overs': inning.overs,
            'performances': [p.to_dict() for p in performances]
        })
    
    return jsonify({
        'match': match.to_dict(),
        'innings': innings_data
    })

@app.route(f'{Config.API_PREFIX}/matches/live', methods=['GET'])
def get_live_matches():
    """Получение live матчей"""
    live_matches = Match.query.filter_by(status='live').all()
    return jsonify({
        'matches': [match.to_dict() for match in live_matches],
        'count': len(live_matches)
    })

# --- Команды ---

@app.route(f'{Config.API_PREFIX}/teams', methods=['GET'])
def get_teams():
    """Получение списка команд"""
    teams = Team.query.all()
    return jsonify({
        'teams': [team.to_dict() for team in teams],
        'total': len(teams)
    })

@app.route(f'{Config.API_PREFIX}/teams/<int:team_id>', methods=['GET'])
def get_team(team_id):
    """Получение информации о команде"""
    stats = DatabaseManager.get_team_stats(team_id)
    return jsonify(stats)

@app.route(f'{Config.API_PREFIX}/teams/<int:team_id>/players', methods=['GET'])
def get_team_players(team_id):
    """Получение игроков команды"""
    players = Player.query.filter_by(team_id=team_id).all()
    return jsonify({
        'players': [player.to_dict() for player in players],
        'total': len(players)
    })

# --- Игроки ---

@app.route(f'{Config.API_PREFIX}/players', methods=['GET'])
def get_players():
    """Получение списка игроков"""
    page = request.args.get('page', 1, type=int)
    role = request.args.get('role')
    team_id = request.args.get('team_id', type=int)
    
    query = Player.query
    
    if role:
        query = query.filter_by(role=role)
    if team_id:
        query = query.filter_by(team_id=team_id)
    
    players = query.order_by(Player.full_name).all()
    
    return jsonify({
        'players': [player.to_dict() for player in players],
        'total': len(players)
    })

@app.route(f'{Config.API_PREFIX}/players/<int:player_id>', methods=['GET'])
def get_player(player_id):
    """Получение информации об игроке"""
    stats = DatabaseManager.get_player_stats(player_id)
    return jsonify(stats)

@app.route(f'{Config.API_PREFIX}/players/top', methods=['GET'])
def get_top_players():
    """Получение лучших игроков"""
    by = request.args.get('by', 'runs')
    limit = request.args.get('limit', 10, type=int)
    
    players = DatabaseManager.get_top_players(by, limit)
    
    return jsonify({
        'players': players,
        'sorted_by': by,
        'limit': limit
    })

# --- Статистика ---

@app.route(f'{Config.API_PREFIX}/stats/summary', methods=['GET'])
def get_stats_summary():
    """Получение сводной статистики"""
    total_teams = Team.query.count()
    total_players = Player.query.count()
    total_matches = Match.query.count()
    live_matches = Match.query.filter_by(status='live').count()
    
    return jsonify({
        'total_teams': total_teams,
        'total_players': total_players,
        'total_matches': total_matches,
        'live_matches': live_matches,
        'last_updated': datetime.utcnow().isoformat()
    })

# --- Админские эндпоинты ---

@app.route(f'{Config.API_PREFIX}/admin/scrape', methods=['POST'])
@admin_required
def trigger_scrape():
    """Запуск скрапинга данных"""
    if not scraping_manager.should_scrape():
        return jsonify({
            'status': 'skipped',
            'message': 'Scrape was performed recently',
            'last_scrape': scraping_manager.last_scrape_time.isoformat() if scraping_manager.last_scrape_time else None
        }), 200
    
    try:
        scraped_data = scraping_manager.run_full_scrape()
        
        if scraped_data:
            saved = DatabaseManager.save_scraped_data(scraped_data)
            if saved:
                return jsonify({
                    'status': 'success',
                    'message': f"Scraped {len(scraped_data.get('matches', []))} matches "
                              f"and {len(scraped_data.get('players', []))} players",
                    'timestamp': datetime.utcnow().isoformat()
                })
        
        return jsonify({
            'status': 'error',
            'message': 'Failed to scrape or save data'
        }), 500
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route(f'{Config.API_PREFIX}/admin/clear-cache', methods=['POST'])
@admin_required
def clear_cache():
    """Очистка кэша (демо-функция)"""
    return jsonify({
        'status': 'success',
        'message': 'Cache cleared (demo function)'
    })

# ========== ВЕБ-ИНТЕРФЕЙС ==========

@app.route('/')
def index():
    """Главная страница"""
    recent_matches = DatabaseManager.get_recent_matches(5)
    top_batsmen = DatabaseManager.get_top_players('runs', 5)
    top_bowlers = DatabaseManager.get_top_players('wickets', 5)
    
    return render_template('index.html',
                         recent_matches=recent_matches,
                         top_batsmen=top_batsmen,
                         top_bowlers=top_bowlers)

@app.route('/matches')
def matches_page():
    """Страница со списком матчей"""
    match_type = request.args.get('type', 'all')
    page = request.args.get('page', 1, type=int)
    
    query = Match.query
    
    if match_type != 'all':
        query = query.filter_by(match_type=match_type)
    
    matches = query.order_by(Match.match_date.desc()).paginate(
        page=page, per_page=Config.ITEMS_PER_PAGE, error_out=False
    )
    
    return render_template('matches.html',
                         matches=matches,
                         match_type=match_type)

@app.route('/players')
def players_page():
    """Страница со списком игроков"""
    role = request.args.get('role', 'all')
    team_id = request.args.get('team_id', type=int)
    page = request.args.get('page', 1, type=int)
    
    query = Player.query
    
    if role != 'all':
        query = query.filter_by(role=role)
    if team_id:
        query = query.filter_by(team_id=team_id)
    
    players = query.order_by(Player.full_name).paginate(
        page=page, per_page=Config.ITEMS_PER_PAGE, error_out=False
    )
    
    teams = Team.query.all()
    
    return render_template('players.html',
                         players=players,
                         teams=teams,
                         role=role,
                         selected_team_id=team_id)

@app.route('/teams')
def teams_page():
    """Страница со списком команд"""
    teams = Team.query.all()
    return render_template('teams.html', teams=teams)

@app.route('/admin')
def admin_page():
    """Админская панель"""
    return render_template('admin.html')

@app.route('/api-docs')
def api_docs():
    """Документация API"""
    api_endpoints = [
        {'method': 'GET', 'path': '/api/v1/health', 'description': 'Проверка здоровья API'},
        {'method': 'GET', 'path': '/api/v1/matches', 'description': 'Список матчей'},
        {'method': 'GET', 'path': '/api/v1/matches/live', 'description': 'Live матчи'},
        {'method': 'GET', 'path': '/api/v1/teams', 'description': 'Список команд'},
        {'method': 'GET', 'path': '/api/v1/players', 'description': 'Список игроков'},
        {'method': 'GET', 'path': '/api/v1/players/top', 'description': 'Лучшие игроки'},
        {'method': 'GET', 'path': '/api/v1/stats/summary', 'description': 'Сводная статистика'},
        {'method': 'POST', 'path': '/api/v1/admin/scrape', 'description': 'Запуск скрапинга (требуется аутентификация)'}
    ]
    
    return render_template('api_docs.html', endpoints=api_endpoints)

# ========== ОБРАБОТЧИКИ ОШИБОК ==========

@app.errorhandler(404)
def not_found_error(error):
    """Обработчик ошибки 404"""
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Resource not found'}), 404
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Обработчик ошибки 500"""
    db.session.rollback()
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Internal server error'}), 500
    return render_template('500.html'), 500

# ========== ЗАПУСК ПРИЛОЖЕНИЯ ==========

if __name__ == '__main__':
    print("=" * 50)
    print("Cricket Scores API Application")
    print("=" * 50)
    print(f"API доступно по адресу: http://localhost:5000{Config.API_PREFIX}")
    print(f"Документация API: http://localhost:5000/api-docs")
    print(f"Админ панель: http://localhost:5000/admin")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
