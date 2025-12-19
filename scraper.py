import requests
from bs4 import BeautifulSoup
import time
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
from models import Team, Player, Match
from database import db

class CricketScraper:
    """Класс для скрапинга данных о крикете"""
    
    def __init__(self, config):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': config.USER_AGENT
        })
    
    def scrape_live_matches(self) -> List[Dict]:
        """Скрапинг live матчей"""
        print("Scraping live matches...")
        
        # В реальном проекте здесь был бы парсинг реального сайта
        # Для демонстрации возвращаем тестовые данные
        
        test_matches = [
            {
                'scraped_match_id': 'test_live_1',
                'match_date': datetime.utcnow(),
                'venue': 'Melbourne Cricket Ground',
                'match_type': 'Test',
                'tournament': 'The Ashes',
                'status': 'live',
                'team1': 'Australia',
                'team2': 'England',
                'team1_score': '287/3',
                'team2_score': '325/10',
                'result': 'Australia lead by 38 runs'
            },
            {
                'scraped_match_id': 'test_live_2',
                'match_date': datetime.utcnow(),
                'venue': 'Eden Gardens, Kolkata',
                'match_type': 'ODI',
                'tournament': 'Asia Cup',
                'status': 'live',
                'team1': 'India',
                'team2': 'Pakistan',
                'team1_score': '245/5 (42.3 ov)',
                'team2_score': '243/10 (48.1 ov)',
                'result': 'India need 3 runs to win'
            }
        ]
        
        return self._process_matches(test_matches)
    
    def scrape_recent_matches(self, days: int = 7) -> List[Dict]:
        """Скрапинг завершенных матчей за последние N дней"""
        print(f"Scraping recent matches (last {days} days)...")
        
        # Тестовые данные для демонстрации
        recent_matches = [
            {
                'scraped_match_id': 'test_recent_1',
                'match_date': datetime.utcnow() - timedelta(days=1),
                'venue': 'Lord\'s, London',
                'match_type': 'ODI',
                'tournament': 'ICC World Cup Qualifier',
                'status': 'completed',
                'team1': 'England',
                'team2': 'New Zealand',
                'team1_score': '310/8 (50 ov)',
                'team2_score': '305/9 (50 ov)',
                'result': 'England won by 5 runs',
                'winner': 'England'
            },
            {
                'scraped_match_id': 'test_recent_2',
                'match_date': datetime.utcnow() - timedelta(days=2),
                'venue': 'Dubai International Stadium',
                'match_type': 'T20',
                'tournament': 'ICC T20 World Cup',
                'status': 'completed',
                'team1': 'Pakistan',
                'team2': 'South Africa',
                'team1_score': '185/5 (20 ov)',
                'team2_score': '179/8 (20 ov)',
                'result': 'Pakistan won by 6 runs',
                'winner': 'Pakistan'
            }
        ]
        
        return self._process_matches(recent_matches)
    
    def scrape_player_stats(self, player_ids: Optional[List[str]] = None) -> List[Dict]:
        """Скрапинг статистики игроков"""
        print("Scraping player statistics...")
        
        # Тестовые данные для демонстрации
        test_players = [
            {
                'scraped_id': 'player_001',
                'full_name': 'Virat Kohli',
                'date_of_birth': '1988-11-05',
                'batting_style': 'Right-hand bat',
                'bowling_style': 'Right-arm medium',
                'role': 'batsman',
                'team': 'India',
                'total_runs': 12898,
                'total_wickets': 4,
                'total_matches': 265,
                'highest_score': 183,
                'best_bowling': '1/15'
            },
            {
                'scraped_id': 'player_002',
                'full_name': 'Pat Cummins',
                'date_of_birth': '1993-05-08',
                'batting_style': 'Right-hand bat',
                'bowling_style': 'Right-arm fast',
                'role': 'bowler',
                'team': 'Australia',
                'total_runs': 876,
                'total_wickets': 216,
                'total_matches': 77,
                'highest_score': 63,
                'best_bowling': '6/23'
            }
        ]
        
        return test_players
    
    def scrape_match_details(self, match_id: str) -> Optional[Dict]:
        """Скрапинг детальной информации о матче"""
        print(f"Scraping details for match {match_id}...")
        
        # Тестовые данные для демонстрации
        return {
            'scraped_match_id': match_id,
            'innings': [
                {
                    'innings_number': 1,
                    'batting_team': 'India',
                    'bowling_team': 'Australia',
                    'total_runs': 328,
                    'wickets': 7,
                    'overs': 50.0,
                    'player_performances': [
                        {
                            'player': 'Virat Kohli',
                            'runs_scored': 120,
                            'balls_faced': 110,
                            'fours': 12,
                            'sixes': 2,
                            'strike_rate': 109.09,
                            'is_out': True,
                            'dismissal_type': 'caught'
                        }
                    ]
                }
            ]
        }
    
    def _process_matches(self, raw_matches: List[Dict]) -> List[Dict]:
        """Обработка скрапированных данных матчей"""
        processed = []
        
        for match in raw_matches:
            # Находим или создаем команды
            team1 = self._get_or_create_team(match.pop('team1'))
            team2 = self._get_or_create_team(match.pop('team2'))
            winner = self._get_or_create_team(match.pop('winner', None))
            
            processed.append({
                **match,
                'team1_id': team1.id if team1 else None,
                'team2_id': team2.id if team2 else None,
                'winner_id': winner.id if winner else None
            })
        
        return processed
    
    def _get_or_create_team(self, team_name: Optional[str]) -> Optional[Team]:
        """Получение или создание команды"""
        if not team_name:
            return None
        
        team = Team.query.filter_by(name=team_name).first()
        if not team:
            team = Team(name=team_name)
            db.session.add(team)
            db.session.commit()
        
        return team
    
    def _parse_score_string(self, score_str: str) -> Tuple[int, int]:
        """Парсинг строки со счетом (например, '287/3')"""
        if not score_str:
            return 0, 0
        
        match = re.match(r'(\d+)/(\d+)', score_str)
        if match:
            return int(match.group(1)), int(match.group(2))
        
        return 0, 0

class ScrapingManager:
    """Менеджер управления скрапингом"""
    
    def __init__(self, config):
        self.config = config
        self.scraper = CricketScraper(config)
        self.last_scrape_time = None
    
    def run_full_scrape(self) -> Dict[str, Any]:
        """Запуск полного скрапинга"""
        print("Starting full scrape...")
        
        all_data = {
            'matches': [],
            'players': []
        }
        
        try:
            # Скрапинг live матчей
            live_matches = self.scraper.scrape_live_matches()
            all_data['matches'].extend(live_matches)
            
            # Скрапинг завершенных матчей
            recent_matches = self.scraper.scrape_recent_matches()
            all_data['matches'].extend(recent_matches)
            
            # Скрапинг статистики игроков
            player_stats = self.scraper.scrape_player_stats()
            all_data['players'].extend(player_stats)
            
            self.last_scrape_time = datetime.utcnow()
            
            print(f"Scrape completed: {len(all_data['matches'])} matches, "
                  f"{len(all_data['players'])} players")
            
            return all_data
            
        except Exception as e:
            print(f"Error during scraping: {e}")
            return {}
    
    def should_scrape(self) -> bool:
        """Проверка необходимости запуска скрапинга"""
        if not self.last_scrape_time:
            return True
        
        time_since_last = datetime.utcnow() - self.last_scrape_time
        return time_since_last >= self.config.SCRAPE_INTERVAL