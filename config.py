import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    
    # Автоматическое определение пути к БД
    if os.environ.get('RENDER'):
        DATABASE_PATH = '/tmp/cricket.db'
    else:
        DATABASE_PATH = 'instance/cricket.db'
        os.makedirs('instance', exist_ok=True)
    
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_PATH}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Настройки для актуальных данных
    API_PREFIX = '/api/v1'
    ITEMS_PER_PAGE = 20
    LAST_UPDATE = datetime.now().strftime('%d.%m.%Y %H:%M')
