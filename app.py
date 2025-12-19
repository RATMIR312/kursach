from flask import Flask, jsonify, request, render_template
from scraper import fetch_live_matches, get_match_details
from score_calculator import calculate_batting_points, calculate_bowling_points

app = Flask(__name__)

# Базовый маршрут - документация API
@app.route('/')
def index():
    return render_template('index.html')

# Маршрут для получения списка активных матчей
@app.route('/api/matches', methods=['GET'])
def get_matches():
    try:
        matches = fetch_live_matches()
        if matches:
            return jsonify({
                "status": "success",
                "count": len(matches),
                "matches": matches
            })
        else:
            return jsonify({
                "status": "success",
                "message": "No live matches found at the moment",
                "matches": []
            }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to fetch matches: {str(e)}"
        }), 500

# Маршрут для получения деталей конкретного матча
@app.route('/api/match/<match_id>', methods=['GET'])
def get_match(match_id):
    try:
        match_details = get_match_details(match_id)
        if match_details:
            return jsonify({
                "status": "success",
                "match": match_details
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Match not found or data unavailable"
            }), 404
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to fetch match details: {str(e)}"
        }), 500

# Маршрут для расчета очков игрока (пример с mock-данными)
@app.route('/api/calculate/player', methods=['POST'])
def calculate_player_points():
    try:
        data = request.json
        
        # Валидация входных данных
        if not data or 'player_type' not in data:
            return jsonify({
                "status": "error",
                "message": "Missing required data: 'player_type' (must be 'batsman' or 'bowler')"
            }), 400
        
        player_type = data.get('player_type')
        
        # Расчет очков в зависимости от типа игрока
        if player_type == 'batsman':
            # Примерные данные отбивающего
            batting_data = {
                'runs': data.get('runs', 0),
                'balls_faced': data.get('balls_faced', 0),
                'fours': data.get('fours', 0),
                'sixes': data.get('sixes', 0),
                'dismissal_type': data.get('dismissal_type', 'not_out')
            }
            points = calculate_batting_points(batting_data)
            
        elif player_type == 'bowler':
            # Примерные данные боулера
            bowling_data = {
                'wickets': data.get('wickets', 0),
                'runs_conceded': data.get('runs_conceded', 0),
                'overs_bowled': data.get('overs_bowled', 0),
                'maidens': data.get('maidens', 0)
            }
            points = calculate_bowling_points(bowling_data)
            
        else:
            return jsonify({
                "status": "error",
                "message": "Invalid player_type. Must be 'batsman' or 'bowler'"
            }), 400
        
        return jsonify({
            "status": "success",
            "player_type": player_type,
            "points": points,
            "data_used": data
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Calculation failed: {str(e)}"
        }), 500

# Маршрут для проверки работоспособности API
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "Cricket Score API",
        "version": "1.0"
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)