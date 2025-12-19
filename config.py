import os
from datetime import timedelta

class Config:
    """Конфигурация приложения"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Настройки базы данных
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    DATABASE_PATH = os.path.join(BASE_DIR, 'instance', 'cricket.db')
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_PATH}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Настройки скрапинга
    SCRAPE_INTERVAL = timedelta(hours=1)  # Интервал обновления данных
    MAX_RETRIES = 3  # Максимальное количество попыток скрапинга
    REQUEST_TIMEOUT = 30  # Таймаут запросов в секундах
    
    # URL для скрапинга (пример - ESPN Cricinfo)
    SCRAPE_URLS = {
        'live_matches': 'https://www.espncricinfo.com/live-cricket-score',
        'recent_matches': 'https://www.espncricinfo.com/recent-matches',
        'player_stats': 'https://www.espncricinfo.com/players'
    }
    
    # User-Agent для запросов
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    
    # Настройки API
    API_PREFIX = '/api/v1'
    ITEMS_PER_PAGE = 20
    
    # Админские настройки
    ADMIN_USERNAME = 'admin'
    ADMIN_PASSWORD = 'cricket123'  # В продакшене использовать переменные окружения