from typing import Dict, Any

def calculate_batting_points(batting_data: Dict[str, Any]) -> float:
    """
    Рассчитывает фэнтези-очки для отбивающего (batsman).
    """
    points = 0.0
    
    # Базовые очки за раны
    runs = batting_data.get('runs', 0)
    points += runs * 1.0
    
    # Бонус за ударные раны
    balls_faced = batting_data.get('balls_faced', 1)  # избегаем деления на 0
    strike_rate = (runs / balls_faced) * 100 if balls_faced > 0 else 0
    
    if strike_rate > 140:
        points += 20  # бонус за высокий strike rate
    elif strike_rate > 120:
        points += 10
    elif strike_rate < 60:
        points -= 10  # штраф за низкий strike rate
    
    # Бонус за границы
    fours = batting_data.get('fours', 0)
    sixes = batting_data.get('sixes', 0)
    
    points += fours * 0.5   # +0.5 за каждую 4
    points += sixes * 1.0   # +1.0 за каждую 6
    
    # Очки за половину века и века
    if runs >= 100:
        points += 25  # бонус за 100 ранов
    elif runs >= 50:
        points += 10  # бонус за 50 ранов
    
    # Штраф за способ выбывания
    dismissal = batting_data.get('dismissal_type', 'not_out')
    if dismissal == 'bowled' or dismissal == 'lbw':
        points -= 5
    elif dismissal == 'not_out':
        points += 10  # бонус за not out
    
    return round(points, 2)

def calculate_bowling_points(bowling_data: Dict[str, Any]) -> float:
    """
    Рассчитывает фэнтези-очки для боулера.
    """
    points = 0.0
    
    # Очки за уикеты
    wickets = bowling_data.get('wickets', 0)
    points += wickets * 20  # 20 очков за каждый уикет
    
    # Бонус за 3+ и 5+ уикетов в иннинге
    if wickets >= 5:
        points += 25  # бонус за 5 уикетов
    elif wickets >= 3:
        points += 10  # бонус за 3 уикета
    
    # Очки за экономность
    runs_conceded = bowling_data.get('runs_conceded', 0)
    overs_bowled = bowling_data.get('overs_bowled', 1)  # избегаем деления на 0
    
    economy_rate = runs_conceded / overs_bowled if overs_bowled > 0 else float('inf')
    
    if economy_rate < 5.0:
        points += 20  # бонус за экономную игру
    elif economy_rate < 7.0:
        points += 10
    elif economy_rate > 10.0:
        points -= 10  # штраф за дорогую игру
    
    # Бонус за мейдены
    maidens = bowling_data.get('maidens', 0)
    points += maidens * 10  # 10 очков за каждый мейден-овер
    
    return round(points, 2)

def calculate_fielding_points(fielding_data: Dict[str, Any]) -> float:
    """
    Рассчитывает очки за полевую игру (опционально).
    """
    points = 0.0
    
    catches = fielding_data.get('catches', 0)
    stumpings = fielding_data.get('stumpings', 0)
    run_outs = fielding_data.get('run_outs', 0)
    
    points += catches * 10      # 10 очков за каждый кэтч
    points += stumpings * 12    # 12 очков за каждый стампинг
    points += run_outs * 15     # 15 очков за каждый ран-аут
    
    return round(points, 2)