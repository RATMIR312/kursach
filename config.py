import os
from datetime import timedelta

class Config:
    """Конфигурация приложения"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # ПРОСТОЕ РЕШЕНИЕ: Всегда используем /tmp на сервере
    DATABASE_PATH = os.path.join('/tmp', 'cricket.db')
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_PATH}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    SCRAPE_INTERVAL = timedelta(hours=1)
    MAX_RETRIES = 3
    REQUEST_TIMEOUT = 30
    SCRAPE_URLS = {
        'live_matches': 'https://www.cricbuzz.com/cricket-match/live-scores',
        'recent_matches': 'https://www.cricbuzz.com/cricket-match/live-scores/recent-matches'
    }
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    API_PREFIX = '/api/v1'
    ITEMS_PER_PAGE = 20
    ADMIN_USERNAME = 'admin'
    ADMIN_PASSWORD = 'cricket123'
