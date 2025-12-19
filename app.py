from flask import Flask, render_template, request, jsonify
from models import db, Match, Player, PlayerPoints
from scraper import fetch_live_matches
from score_calculator import calculate_batting_points, calculate_bowling_points
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cricket.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Инициализация базы данных
db.init_app(app)

def init_sample_data():
    """Инициализация тестовых данных (аналогично addSample() в ЛР №2)"""
    try:
        # ... (полный код функции init_sample_data остается БЕЗ ИЗМЕНЕНИЙ, как в предыдущем ответе)
        # Проверяем, нет ли уже данных
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

# *** КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: Заменяем старый декоратор ***
# Удаляем строку с @app.before_first_request и переносим логику инициализации
# непосредственно в блок создания таблиц.

# Создание таблиц и инициализация данных при запуске приложения
with app.app_context():
    db.create_all()
    print("✅ Таблицы базы данных созданы/проверены.")
    init_sample_data()  # Добавляем тестовые данные сразу после создания таблиц

# Маршруты для веб-интерфейса
@app.route('/')
def index():
    """Главная страница"""
    # Для отображения статистики на главной странице
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

# REST API endpoint для проверки здоровья
@app.route('/api/health')
def health_check():
    """Проверка работоспособности API и БД"""
    try:
        with app.app_context():
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

# ... (остальные маршруты API, такие как /api/matches, /api/calculate и т.д., 
# остаются БЕЗ ИЗМЕНЕНИЙ, как в коде из предыдущего ответа)

if __name__ == '__main__':
    # Этот блок выполняется только при локальном запуске, а не на Render
    with app.app_context():
        # Дополнительная проверка при локальном запуске
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)
