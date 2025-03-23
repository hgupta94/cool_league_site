CREATE TABLE matchups (
    id VARCHAR(16) PRIMARY KEY,
    season INT,
    week INT,
    team VARCHAR(6),
    opponent VARCHAR(6),
    matchup_result DECIMAL(2, 1),
    tophalf_result DECIMAL(2, 1),
    score DECIMAL(6, 2),
    created timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
