CREATE TABLE h2h (
    id VARCHAR(255) PRIMARY KEY,
    season INT,
    week INT,
    team VARCHAR(255),
    opp VARCHAR(255),
    result DECIMAL(2, 1), --number of wins team1 has vs team2
    created timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
