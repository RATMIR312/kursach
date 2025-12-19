import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # ПУТЬ К БАЗЕ ДАННЫХ
    if os.environ.get('RENDER'):
        DATABASE_PATH = '/tmp/cricket.db'
    else:
        BASE_DIR = os.path.abspath(os.path.dirname(__file__))
        DATABASE_PATH = os.path.join(BASE_DIR, 'instance', 'cricket.db')
        os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_PATH}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # НАСТРОЙКИ ПЛАНИРОВЩИКА
    SCHEDULER_API_ENABLED = True
    
    # НАСТРОЙКИ ПРИЛОЖЕНИЯ
    API_PREFIX = '/api/v1'
    ITEMS_PER_PAGE = 20
    AUTO_UPDATE_INTERVAL_HOURS = 6  # Интервал автоматического обновления
