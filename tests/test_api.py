import unittest
import json
from app import app
from models import db

class APITestCase(unittest.TestCase):
    """Тесты для API эндпоинтов"""
    
    def setUp(self):
        """Настройка тестового окружения"""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app.test_client()
        
        with app.app_context():
            db.create_all()
    
    def tearDown(self):
        """Очистка после тестов"""
        with app.app_context():
            db.session.remove()
            db.drop_all()
    
    def test_health_check(self):
        """Тест проверки здоровья API"""
        response = self.app.get('/api/v1/health')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')
        self.assertIn('version', data)
    
    def test_get_matches(self):
        """Тест получения списка матчей"""
        response = self.app.get('/api/v1/matches')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('matches', data)
        self.assertIn('total', data)
    
    def test_get_teams(self):
        """Тест получения списка команд"""
        response = self.app.get('/api/v1/teams')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('teams', data)
    
    def test_get_players(self):
        """Тест получения списка игроков"""
        response = self.app.get('/api/v1/players')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('players', data)
    
    def test_404_error(self):
        """Тест обработки 404 ошибки"""
        response = self.app.get('/api/v1/nonexistent')
        self.assertEqual(response.status_code, 404)
        
        data = json.loads(response.data)
        self.assertIn('error', data)

if __name__ == '__main__':
    unittest.main()