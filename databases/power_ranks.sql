CREATE TABLE power_ranks (
    id VARCHAR(255) PRIMARY KEY,
    season INT,
    week INT,
    team VARCHAR(255),
    team_rank INT,
    power_rank INT,
    power_score DECIMAL,
    power_rank_change INT,
    power_score_change DECIMAL,
    created timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
