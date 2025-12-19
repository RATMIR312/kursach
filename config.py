import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    
    # Путь к базе данных для Render
    if os.environ.get('RENDER'):
        # На Render используем временную директорию
        DATABASE_PATH = '/tmp/cricket.db'
    else:
        # Локально
        BASE_DIR = os.path.abspath(os.path.dirname(__file__))
        DATABASE_PATH = os.path.join(BASE_DIR, 'instance', 'cricket.db')
        os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_PATH}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Настройки планировщика
    SCHEDULER_API_ENABLED = True
    SCHEDULER_TIMEZONE = "UTC"
    
    # Настройки приложения
    API_PREFIX = '/api/v1'
    ITEMS_PER_PAGE = 20
