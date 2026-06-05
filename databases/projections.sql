CREATE TABLE player_stats (
    id VARCHAR(50) PRIMARY KEY,
    season INT,
    week INT,
    espn_id INT,
    fp_id INT,
    name VARCHAR(50),
    position VARCHAR(4),
    team_id INT,
    lineup_slot VARCHAR(4),
    actual DECIMAL(4, 2),
    projection DECIMAL(4, 2),
    source VARCHAR(4),
    ppr FLOAT,
    created timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
