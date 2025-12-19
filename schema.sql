-- Схема базы данных для Cricket Scores API

-- Таблица команд
CREATE TABLE IF NOT EXISTS teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE,
    short_name VARCHAR(10),
    country VARCHAR(50),
    founded_year INTEGER,
    logo_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица игроков
CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name VARCHAR(100) NOT NULL,
    date_of_birth DATE,
    batting_style VARCHAR(50),
    bowling_style VARCHAR(50),
    role VARCHAR(50) CHECK (role IN ('batsman', 'bowler', 'all-rounder', 'wicket-keeper')),
    team_id INTEGER,
    image_url VARCHAR(500),
    scraped_id VARCHAR(50) UNIQUE,
    
    -- Статистика
    total_runs INTEGER DEFAULT 0,
    total_wickets INTEGER DEFAULT 0,
    total_matches INTEGER DEFAULT 0,
    highest_score INTEGER DEFAULT 0,
    best_bowling VARCHAR(20),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (team_id) REFERENCES teams(id)
);

-- Таблица матчей
CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_date TIMESTAMP NOT NULL,
    venue VARCHAR(200),
    match_type VARCHAR(50),
    tournament VARCHAR(100),
    status VARCHAR(50),
    
    -- Команды
    team1_id INTEGER,
    team2_id INTEGER,
    winner_id INTEGER,
    
    -- Счет
    team1_score VARCHAR(50),
    team2_score VARCHAR(50),
    team1_overs FLOAT,
    team2_overs FLOAT,
    result VARCHAR(200),
    
    -- Внешний ID
    scraped_match_id VARCHAR(50) UNIQUE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (team1_id) REFERENCES teams(id),
    FOREIGN KEY (team2_id) REFERENCES teams(id),
    FOREIGN KEY (winner_id) REFERENCES teams(id)
);

-- Таблица иннингов
CREATE TABLE IF NOT EXISTS innings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id INTEGER NOT NULL,
    innings_number INTEGER,
    batting_team_id INTEGER,
    bowling_team_id INTEGER,
    
    -- Статистика
    total_runs INTEGER DEFAULT 0,
    wickets INTEGER DEFAULT 0,
    overs FLOAT DEFAULT 0.0,
    extras INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (match_id) REFERENCES matches(id),
    FOREIGN KEY (batting_team_id) REFERENCES teams(id),
    FOREIGN KEY (bowling_team_id) REFERENCES teams(id)
);

-- Таблица выступлений игроков
CREATE TABLE IF NOT EXISTS player_performances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL,
    innings_id INTEGER NOT NULL,
    
    -- Бэттинг
    runs_scored INTEGER DEFAULT 0,
    balls_faced INTEGER DEFAULT 0,
    fours INTEGER DEFAULT 0,
    sixes INTEGER DEFAULT 0,
    strike_rate FLOAT,
    is_out BOOLEAN DEFAULT FALSE,
    dismissal_type VARCHAR(50),
    
    -- Боулинг
    overs_bowled FLOAT DEFAULT 0.0,
    maidens INTEGER DEFAULT 0,
    runs_given INTEGER DEFAULT 0,
    wickets_taken INTEGER DEFAULT 0,
    economy_rate FLOAT,
    wide_balls INTEGER DEFAULT 0,
    no_balls INTEGER DEFAULT 0,
    
    -- Полевая
    catches INTEGER DEFAULT 0,
    stumpings INTEGER DEFAULT 0,
    run_outs INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (player_id) REFERENCES players(id),
    FOREIGN KEY (innings_id) REFERENCES innings(id)
);

-- Таблица настроек
CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key VARCHAR(100) UNIQUE NOT NULL,
    value TEXT,
    description VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица логов скрапинга
CREATE TABLE IF NOT EXISTS scraping_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scrape_type VARCHAR(50),
    items_scraped INTEGER DEFAULT 0,
    status VARCHAR(20),
    error_message TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds INTEGER
);

-- Индексы для улучшения производительности
CREATE INDEX IF NOT EXISTS idx_players_team ON players(team_id);
CREATE INDEX IF NOT EXISTS idx_players_scraped ON players(scraped_id);
CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(match_date);
CREATE INDEX IF NOT EXISTS idx_matches_status ON matches(status);
CREATE INDEX IF NOT EXISTS idx_matches_teams ON matches(team1_id, team2_id);
CREATE INDEX IF NOT EXISTS idx_matches_scraped ON matches(scraped_match_id);
CREATE INDEX IF NOT EXISTS idx_innings_match ON innings(match_id);
CREATE INDEX IF NOT EXISTS idx_performances_player ON player_performances(player_id);
CREATE INDEX IF NOT EXISTS idx_performances_innings ON player_performances(innings_id);

-- Триггер для обновления времени
CREATE TRIGGER IF NOT EXISTS update_teams_timestamp 
AFTER UPDATE ON teams 
BEGIN
    UPDATE teams SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_players_timestamp 
AFTER UPDATE ON players 
BEGIN
    UPDATE players SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_matches_timestamp 
AFTER UPDATE ON matches 
BEGIN
    UPDATE matches SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Вставка начальных настроек
INSERT OR IGNORE INTO settings (key, value, description) VALUES
    ('scrape_interval', '1', 'Интервал скрапинга в часах'),
    ('last_scrape', '', 'Время последнего скрапинга'),
    ('api_rate_limit', '60', 'Лимит запросов в минуту'),
    ('maintenance_mode', 'false', 'Режим обслуживания');