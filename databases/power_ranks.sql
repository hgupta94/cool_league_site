CREATE TABLE power_ranks (
    id VARCHAR(255) PRIMARY KEY,
    season INT,
    week INT,
    team VARCHAR(255),
    season_idx DECIMAL(5, 4),
    week_idx DECIMAL(5, 4),
    consistency_idx DECIMAL(5, 4),
    luck_idx DECIMAL(5, 4),
    power_score_raw DECIMAL(5, 4),
    power_score_norm DECIMAL(5, 4),
    power_rank INT,
    created timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
