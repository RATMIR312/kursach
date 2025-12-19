# app.py - Cricket Scores API с автоматическим обновлением
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from flask_apscheduler import APScheduler
from datetime import datetime, timedelta
import atexit
import os
import sys

# Добавляем текущую директорию в путь для импорта модулей
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config
from models import db, Team, Player, Match
from database import DatabaseManager

# Инициализация приложения
app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

# Инициализация базы данных
db.init_app(app)

# Инициализация планировщика
scheduler = APScheduler()
scheduler.init_app(app)

# Глобальная переменная для отслеживания последнего обновления
last_update_time = None

def update_cricket_data():
    """Функция для обновления данных о крикете"""
    global last_update_time
    
    try:
        print(f"[{datetime.now()}] Запуск автоматического обновления данных...")
        
        with app.app_context():
            # Здесь будет ваш код для скрапинга данных
            # Временно создаем тестовые актуальные данные
            
            # Создаем команды если их нет
            if not Team.query.first():
                print("Создание начальных данных...")
                DatabaseManager._create_sample_data()
            
            # Обновляем статусы матчей
            matches = Match.query.all()
            for match in matches:
                # Пример логики обновления:
                # Если матч "live" и дата старше 8 часов - завершаем его
                if match.status == 'live' and match.match_date:
                    time_diff = datetime.utcnow() - match.match_date
                    if time_diff > timedelta(hours=8):
                        match.status = 'completed'
                        if not match.result:
                            match.result = "Матч завершен"
                        db.session.commit()
                        print(f"Матч {match.id} переведен в статус 'completed'")
            
            # Обновляем время последнего обновления
            last_update_time = datetime.now()
            print(f"[{datetime.now()}] Обновление завершено успешно!")
            
            return True
            
    except Exception as e:
        print(f"Ошибка при обновлении данных: {str(e)}")
        return False

def scheduled_update():
    """Запланированное обновление данных"""
    update_cricket_data()

# Конфигурация планировщика
class SchedulerConfig:
    SCHEDULER_API_ENABLED = True
    SCHEDULER_TIMEZONE = "UTC"

app.config.from_object(SchedulerConfig)

@scheduler.task('interval', id='auto_update', hours=6, misfire_grace_time=900)
def auto_update_job():
    """Автоматическое обновление каждые 6 часов"""
    scheduled_update()

@scheduler.task('interval', id='daily_summary', days=1, misfire_grace_time=3600)
def daily_summary_job():
    """Ежедневная сводка"""
    print(f"[{datetime.now()}] Ежедневная проверка данных выполнена")

# API для ручного запуска обновления
@app.route('/api/v1/admin/update-now', methods=['POST'])
def manual_update():
    """Ручной запуск обновления данных"""
    try:
        success = update_cricket_data()
        if success:
            return jsonify({
                'status': 'success',
                'message': 'Данные успешно обновлены',
                'last_update': last_update_time.strftime('%Y-%m-%d %H:%M:%S') if last_update_time else None
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Произошла ошибка при обновлении'
            }), 500
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/v1/health', methods=['GET'])
def health_check():
    """Проверка здоровья API"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0',
        'last_update': last_update_time.isoformat() if last_update_time else None,
        'scheduler_running': scheduler.running
    })

# ========== API ЭНДПОИНТЫ ==========

@app.route('/api/v1/matches', methods=['GET'])
def get_matches():
    """Получение списка матчей"""
    match_type = request.args.get('type', 'all')
    status = request.args.get('status')
    limit = request.args.get('limit', type=int)
    
    query = Match.query
    
    if match_type != 'all':
        query = query.filter_by(match_type=match_type)
    if status:
        query = query.filter_by(status=status)
    
    if limit:
        matches = query.order_by(Match.match_date.desc()).limit(limit).all()
    else:
        matches = query.order_by(Match.match_date.desc()).all()
    
    return jsonify({
        'matches': [match.to_dict() for match in matches],
        'total': len(matches),
        'last_update': last_update_time.isoformat() if last_update_time else None
    })

@app.route('/api/v1/matches/<int:match_id>', methods=['GET'])
def get_match(match_id):
    """Получение информации о конкретном матче"""
    match = Match.query.get_or_404(match_id)
    return jsonify(match.to_dict())

@app.route('/api/v1/matches/live', methods=['GET'])
def get_live_matches():
    """Получение live матчей"""
    live_matches = Match.query.filter_by(status='live').order_by(Match.match_date.desc()).all()
    return jsonify({
        'matches': [match.to_dict() for match in live_matches],
        'count': len(live_matches)
    })

@app.route('/api/v1/teams', methods=['GET'])
def get_teams():
    """Получение списка команд"""
    teams = Team.query.all()
    return jsonify({
        'teams': [team.to_dict() for team in teams],
        'total': len(teams)
    })

@app.route('/api/v1/teams/<int:team_id>', methods=['GET'])
def get_team(team_id):
    """Получение информации о команде"""
    stats = DatabaseManager.get_team_stats(team_id)
    return jsonify(stats)

@app.route('/api/v1/players', methods=['GET'])
def get_players():
    """Получение списка игроков"""
    role = request.args.get('role')
    team_id = request.args.get('team_id', type=int)
    limit = request.args.get('limit', type=int)
    
    query = Player.query
    
    if role:
        query = query.filter_by(role=role)
    if team_id:
        query = query.filter_by(team_id=team_id)
    
    if limit:
        players = query.order_by(Player.full_name).limit(limit).all()
    else:
        players = query.order_by(Player.full_name).all()
    
    return jsonify({
        'players': [player.to_dict() for player in players],
        'total': len(players)
    })

@app.route('/api/v1/players/<int:player_id>', methods=['GET'])
def get_player(player_id):
    """Получение информации об игроке"""
    stats = DatabaseManager.get_player_stats(player_id)
    return jsonify(stats)

@app.route('/api/v1/players/top', methods=['GET'])
def get_top_players():
    """Получение лучших игроков"""
    by = request.args.get('by', 'runs')
    limit = request.args.get('limit', 10, type=int)
    
    if by == 'runs':
        players = Player.query.order_by(Player.total_runs.desc()).limit(limit).all()
    elif by == 'wickets':
        players = Player.query.order_by(Player.total_wickets.desc()).limit(limit).all()
    else:
        players = Player.query.order_by(Player.total_matches.desc()).limit(limit).all()
    
    return jsonify({
        'players': [player.to_dict() for player in players],
        'sorted_by': by,
        'limit': limit
    })

@app.route('/api/v1/stats/summary', methods=['GET'])
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
        'last_update': datetime.utcnow().isoformat(),
        'auto_update_enabled': scheduler.running
    })

# ========== ВЕБ-ИНТЕРФЕЙС ==========

@app.route('/')
def index():
    """Главная страница"""
    recent_matches = Match.query.order_by(Match.match_date.desc()).limit(5).all()
    top_batsmen = Player.query.order_by(Player.total_runs.desc()).limit(5).all()
    top_bowlers = Player.query.order_by(Player.total_wickets.desc()).limit(5).all()
    
    return render_template('index.html',
                         recent_matches=[m.to_dict() for m in recent_matches],
                         top_batsmen=[p.to_dict() for p in top_batsmen],
                         top_bowlers=[p.to_dict() for p in top_bowlers],
                         last_update=last_update_time)

@app.route('/matches')
def matches_page():
    """Страница со списком матчей"""
    match_type = request.args.get('type', 'all')
    page = request.args.get('page', 1, type=int)
    
    query = Match.query
    
    if match_type != 'all':
        query = query.filter_by(match_type=match_type)
    
    matches = query.order_by(Match.match_date.desc()).paginate(
        page=page, per_page=app.config['ITEMS_PER_PAGE'], error_out=False
    )
    
    return render_template('matches.html',
                         matches=matches,
                         match_type=match_type,
                         last_update=last_update_time)

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
        page=page, per_page=app.config['ITEMS_PER_PAGE'], error_out=False
    )
    
    teams = Team.query.all()
    
    return render_template('players.html',
                         players=players,
                         teams=teams,
                         role=role,
                         selected_team_id=team_id,
                         last_update=last_update_time)

@app.route('/teams')
def teams_page():
    """Страница со списком команд"""
    teams = Team.query.all()
    total_players = Player.query.count()
    
    return render_template('teams.html',
                         teams=teams,
                         total_players=total_players,
                         last_update=last_update_time)

@app.route('/admin')
def admin_page():
    """Админская панель"""
    stats = {
        'total_teams': Team.query.count(),
        'total_players': Player.query.count(),
        'total_matches': Match.query.count(),
        'live_matches': Match.query.filter_by(status='live').count()
    }
    
    return render_template('admin.html',
                         stats=stats,
                         last_update=last_update_time,
                         scheduler_status=scheduler.running)

@app.route('/api-docs')
def api_docs():
    """Документация API"""
    return render_template('api_docs.html',
                         last_update=last_update_time)

# ========== ОБРАБОТЧИКИ ОШИБОК ==========

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

# ========== ИНИЦИАЛИЗАЦИЯ ПРИЛОЖЕНИЯ ==========

def init_database():
    """Инициализация базы данных при запуске"""
    with app.app_context():
        try:
            # Создаем все таблицы
            db.create_all()
            print("✅ Таблицы базы данных созданы")
            
            # Создаем начальные данные если база пустая
            if not Team.query.first():
                print("🔄 Создание начальных данных...")
                DatabaseManager._create_sample_data()
                print("✅ Начальные данные созданы")
            
            # Запускаем первоначальное обновление
            global last_update_time
            update_cricket_data()
            last_update_time = datetime.now()
            
        except Exception as e:
            print(f"⚠️ Ошибка при инициализации базы данных: {e}")

def shutdown_scheduler():
    """Корректное завершение работы планировщика"""
    if scheduler.running:
        scheduler.shutdown()
        print("Планировщик остановлен")

# Регистрируем функцию завершения
atexit.register(shutdown_scheduler)

# ========== ЗАПУСК ПРИЛОЖЕНИЯ ==========

if __name__ == '__main__':
    # Инициализируем базу данных
    init_database()
    
    # Запускаем планировщик
    if not scheduler.running:
        scheduler.start()
        print("✅ Планировщик задач запущен")
        print(f"📅 Автоматическое обновление настроено на каждые 6 часов")
    
    print("=" * 50)
    print("🏏 Cricket Scores API Application")
    print("=" * 50)
    print(f"📍 API доступно по адресу: http://localhost:5000{app.config['API_PREFIX']}")
    print(f"📖 Документация API: http://localhost:5000/api-docs")
    print(f"⚙️ Админ панель: http://localhost:5000/admin")
    print(f"🔄 Ручное обновление: POST http://localhost:5000/api/v1/admin/update-now")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
else:
    # Для запуска через Gunicorn (на Render)
    init_database()
    if not scheduler.running:
        scheduler.start()
        print("✅ Планировщик задач запущен в режиме production")
