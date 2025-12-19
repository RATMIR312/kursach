import unittest
from unittest.mock import Mock, patch
from scraper import CricketScraper, ScrapingManager
from config import Config

class ScraperTestCase(unittest.TestCase):
    """Тесты для модуля скрапинга"""
    
    def setUp(self):
        """Настройка тестового окружения"""
        self.config = Config
        self.scraper = CricketScraper(self.config)
    
    def test_scraper_initialization(self):
        """Тест инициализации скрапера"""
        self.assertIsNotNone(self.scraper.session)
        self.assertEqual(self.scraper.session.headers['User-Agent'], Config.USER_AGENT)
    
    @patch('scraper.requests.Session.get')
    def test_scrape_live_matches(self, mock_get):
        """Тест скрапинга live матчей"""
        # Мокаем ответ от сервера
        mock_response = Mock()
        mock_response.content = '<html><body>Test content</body></html>'
        mock_get.return_value = mock_response
        
        # Вызываем метод скрапинга
        matches = self.scraper.scrape_live_matches()
        
        # Проверяем результат
        self.assertIsInstance(matches, list)
        # В тестовом режиме возвращаются тестовые данные
        self.assertTrue(len(matches) > 0)
    
    def test_parse_score_string(self):
        """Тест парсинга строки со счетом"""
        # Тест с корректной строкой
        runs, wickets = self.scraper._parse_score_string('287/3')
        self.assertEqual(runs, 287)
        self.assertEqual(wickets, 3)
        
        # Тест с некорректной строкой
        runs, wickets = self.scraper._parse_score_string('invalid')
        self.assertEqual(runs, 0)
        self.assertEqual(wickets, 0)
        
        # Тест с пустой строкой
        runs, wickets = self.scraper._parse_score_string('')
        self.assertEqual(runs, 0)
        self.assertEqual(wickets, 0)
    
    def test_scraping_manager(self):
        """Тест менеджера скрапинга"""
        manager = ScrapingManager(self.config)
        
        # Проверяем инициализацию
        self.assertIsNotNone(manager.scraper)
        self.assertIsNone(manager.last_scrape_time)
        
        # Проверяем условие скрапинга
        self.assertTrue(manager.should_scrape())

if __name__ == '__main__':
    unittest.main()