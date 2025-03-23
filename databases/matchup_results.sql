CREATE TABLE matchups (
    id VARCHAR(16) PRIMARY KEY,
    season INT,
    week INT,
    team VARCHAR(6),
    opponent VARCHAR(6),
    matchup_result DECIMAL,
    tophalf_result DECIMAL,
    points DECIMAL,
    created timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
