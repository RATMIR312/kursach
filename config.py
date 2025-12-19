import os
from datetime import timedelta

class Config:
    """Конфигурация приложения"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # ИСПРАВЛЕННЫЙ ПУТЬ ДЛЯ RENDER
    if os.environ.get('RENDER'):
        # На Render используем /tmp
        DATABASE_PATH = os.path.join('/tmp', 'cricket.db')
    else:
        # Локально используем instance/
        BASE_DIR = os.path.abspath(os.path.dirname(__file__))
        DATABASE_PATH = os.path.join(BASE_DIR, 'instance', 'cricket.db')
        os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    
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
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'cricket123')
