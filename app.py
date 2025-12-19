from flask import Flask, render_template, request, jsonify
from models import db, Match, Player, PlayerPoints
from scraper import fetch_live_matches  # ТОЛЬКО fetch_live_matches
from score_calculator import calculate_batting_points, calculate_bowling_points
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cricket.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def init_sample_data():
    """Инициализация тестовых данных"""
    try:
        if Match.query.count() > 0:
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
    init_sample_data()

# Веб-интерфейс
@app.route('/')
def index():
    matches_count = Match.query.count()
    players_count = Player.query.count()
    calculations_count = PlayerPoints.query.count()
    return render_template('index.html', 
                          matches_count=matches_count,
                          players_count=players_count,
                          calculations_count=calculations_count)

@app.route('/matches')
def matches_page():
    matches = Match.query.all()
    return render_template('matches.html', matches=matches)

@app.route('/players')
def players_page():
    players = Player.query.all()
    return render_template('players.html', players=players)

@app.route('/calculate')
def calculate_page():
    players = Player.query.all()
    return render_template('calculate.html', players=players)

@app.route('/admin')
def admin_page():
    matches = Match.query.all()
    players = Player.query.all()
    points_history = PlayerPoints.query.order_by(PlayerPoints.calculation_date.desc()).limit(10).all()
    return render_template('admin.html', matches=matches, players=players, points_history=points_history)

# API endpoints
@app.route('/api/health')
def health_check():
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
    try:
        matches = Match.query.all()
        return jsonify([match.to_dict() for match in matches])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/players', methods=['GET'])
def get_players_api():
    try:
        role = request.args.get('role')
        team = request.args.get('team')
        
        query = Player.query
        if role:
            query = query.filter_by(role=role)
        if team:
            query = query.filter_by(team=team)
        
        players = query.all()
        return jsonify([player.to_dict() for player in players])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/calculate', methods=['POST'])
def calculate_points_api():
    try:
        data = request.json
        player_id = data.get('player_id')
        
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
        
        player_points = PlayerPoints(
            player_id=player_id,
            match_id=data.get('match_id', 1),
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

@app.route('/api/scrape/matches')
def scrape_matches():
    """API эндпоинт для веб-скрапинга"""
    try:
        matches_data = fetch_live_matches()
        
        if not matches_data:
            return jsonify({
                'status': 'success',
                'message': 'Нет данных для добавления',
                'matches_added': 0,
                'total_matches': Match.query.count()
            })
        
        matches_added = 0
        for match_data in matches_data:
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
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f'Добавлено {matches_added} новых матчей',
            'matches_added': matches_added,
            'total_matches': Match.query.count()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f'Ошибка: {str(e)}',
            'matches_added': 0
        }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
