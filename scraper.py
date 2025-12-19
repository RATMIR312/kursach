import requests
from bs4 import BeautifulSoup
import time
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import json
from models import Team, Player, Match
from database import db
import html5lib  # Используем html5lib вместо lxml

class CricketScraper:
    """Класс для скрапинга данных о крикете с использованием html5lib"""
    
    def __init__(self, config):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': config.USER_AGENT
        })
    
    def scrape_live_matches(self) -> List[Dict]:
        """Скрапинг live матчей"""
        print("Scraping live matches...")
        
        # Используем html5lib как парсер
        try:
            url = "https://www.cricbuzz.com/cricket-match/live-scores"
            response = self.session.get(url, timeout=self.config.REQUEST_TIMEOUT)
            response.raise_for_status()
            
            # Используем html5lib парсер
            soup = BeautifulSoup(response.content, 'html5lib')

                    # Добавляем проверку на пустой контент
        if not soup or len(soup.find_all()) < 10:
            print("Warning: Page content appears to be empty or invalid")
            return self._get_test_live_matches()
            
            matches = []
            # Поиск матчей (пример селекторов)
            match_cards = soup.find_all('div', class_=re.compile(r'match-card|cb-mtch-lst'))
            
            for card in match_cards[:5]:  # Ограничим 5 матчами для теста
                try:
                    # Пример парсинга структуры
                    teams = card.find_all('span', class_=re.compile(r'team-name|cb-ovr-flo'))
                    scores = card.find_all('span', class_=re.compile(r'score|cb-font-20'))
                    
                    if len(teams) >= 2:
                        match_data = {
                            'scraped_match_id': f"live_{int(time.time())}_{len(matches)}",
                            'match_date': datetime.utcnow(),
                            'venue': self._extract_venue(card),
                            'match_type': self._extract_match_type(card),
                            'tournament': self._extract_tournament(card),
                            'status': 'live',
                            'team1': teams[0].get_text(strip=True),
                            'team2': teams[1].get_text(strip=True),
                            'team1_score': scores[0].get_text(strip=True) if len(scores) > 0 else '',
                            'team2_score': scores[1].get_text(strip=True) if len(scores) > 1 else '',
                            'result': card.find('div', class_=re.compile(r'status|cb-text-live')).get_text(strip=True) if card.find('div', class_=re.compile(r'status|cb-text-live')) else 'In Progress'
                        }
                        matches.append(match_data)
                except Exception as e:
                    print(f"Error parsing match card: {e}")
                    continue
            
            if not matches:
                # Возвращаем тестовые данные если не удалось распарсить
                matches = self._get_test_live_matches()
            
            return self._process_matches(matches)
            
        except Exception as e:
            print(f"Error scraping live matches: {e}")
            # Возвращаем тестовые данные в случае ошибки
            return self._process_matches(self._get_test_live_matches())

        except requests.exceptions.RequestException as e:
            print(f"Network error scraping live matches: {e}")
            return self._process_matches(self._get_test_live_matches())
        except Exception as e:
            print(f"Unexpected error in scrape_live_matches: {e}")
            return []
    
    def scrape_recent_matches(self, days: int = 7) -> List[Dict]:
        """Скрапинг завершенных матчей"""
        print(f"Scraping recent matches (last {days} days)...")
        
        try:
            url = "https://www.cricbuzz.com/cricket-match/live-scores/recent-matches"
            response = self.session.get(url, timeout=self.config.REQUEST_TIMEOUT)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html5lib')
            matches = []
            
            # Поиск завершенных матчей
            match_items = soup.find_all('div', class_=re.compile(r'cb-mtch-lst|cb-col-100'))
            
            for item in match_items[:10]:  # Ограничим 10 матчами
                try:
                    # Проверяем, что матч завершен
                    status_elem = item.find('span', class_=re.compile(r'status|cb-text-complete'))
                    if status_elem and 'complete' in status_elem.get_text(strip=True).lower():
                        teams = item.find_all('span', class_=re.compile(r'team-name|hvr-underline'))
                        scores = item.find_all('span', class_=re.compile(r'score'))
                        
                        if len(teams) >= 2:
                            match_data = {
                                'scraped_match_id': f"recent_{int(time.time())}_{len(matches)}",
                                'match_date': datetime.utcnow() - timedelta(days=len(matches) % days),
                                'venue': self._extract_venue(item),
                                'match_type': self._extract_match_type(item),
                                'tournament': self._extract_tournament(item),
                                'status': 'completed',
                                'team1': teams[0].get_text(strip=True),
                                'team2': teams[1].get_text(strip=True),
                                'team1_score': scores[0].get_text(strip=True) if len(scores) > 0 else '',
                                'team2_score': scores[1].get_text(strip=True) if len(scores) > 1 else '',
                                'result': status_elem.get_text(strip=True),
                                'winner': self._extract_winner(item, teams)
                            }
                            matches.append(match_data)
                except Exception as e:
                    print(f"Error parsing recent match: {e}")
                    continue
            
            if not matches:
                matches = self._get_test_recent_matches(days)
            
            return self._process_matches(matches)
            
        except Exception as e:
            print(f"Error scraping recent matches: {e}")
            return self._process_matches(self._get_test_recent_matches(days))
    
    def _extract_venue(self, element) -> str:
        """Извлечение места проведения"""
        venue_elem = element.find('span', class_=re.compile(r'venue|ground'))
        return venue_elem.get_text(strip=True) if venue_elem else "Unknown Venue"
    
    def _extract_match_type(self, element) -> str:
        """Извлечение типа матча"""
        type_elem = element.find('span', class_=re.compile(r'match-type|format'))
        if type_elem:
            text = type_elem.get_text(strip=True).upper()
            if 'TEST' in text:
                return 'Test'
            elif 'ODI' in text:
                return 'ODI'
            elif 'T20' in text:
                return 'T20'
        return 'ODI'  # По умолчанию
    
    def _extract_tournament(self, element) -> str:
        """Извлечение названия турнира"""
        tournament_elem = element.find('a', class_=re.compile(r'tournament|series'))
        return tournament_elem.get_text(strip=True) if tournament_elem else "International"
    
    def _extract_winner(self, element, teams) -> Optional[str]:
        """Извлечение победителя"""
        result_elem = element.find('span', class_=re.compile(r'result|winner'))
        if result_elem:
            result_text = result_elem.get_text(strip=True)
            for team in teams:
                team_name = team.get_text(strip=True)
                if team_name in result_text:
                    return team_name
        return None
    
    def _get_test_live_matches(self) -> List[Dict]:
        """Тестовые данные для live матчей"""
        return [
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
    
    def _get_test_recent_matches(self, days: int) -> List[Dict]:
        """Тестовые данные для завершенных матчей"""
        return [
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
    
    def scrape_player_stats(self, player_ids: Optional[List[str]] = None) -> List[Dict]:
        """Скрапинг статистики игроков"""
        print("Scraping player statistics...")
        
        # Тестовые данные для демонстрации
        return [
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
        
        # Удаляем оверы если есть
        score_str = re.sub(r'\([^)]+\)', '', score_str).strip()
        
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
