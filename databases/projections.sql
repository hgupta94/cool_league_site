CREATE TABLE projections (
    id VARCHAR(255) PRIMARY KEY,
    espn_id INT,
    season INT,
    week INT,
    receptions FLOAT,
    fantasy_points FLOAT,
    created timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
