CREATE TABLE season_sim (
    id VARCHAR(20) PRIMARY KEY,
    season INT,
    week INT,
    team VARCHAR(6),
    matchup_wins DECIMAL(6, 2),
    tophalf_wins DECIMAL(4, 4),
    total_wins DECIMAL(4, 4),
    playoffs DECIMAL(4, 4),
    finals DECIMAL(4, 4),
    champion DECIMAL(4, 4),
    created timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
