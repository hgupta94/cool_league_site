CREATE TABLE h2h (
    id VARCHAR(24) PRIMARY KEY,
    season INT,
    week INT,
    team VARCHAR(6),
    opponent VARCHAR(6),
    result DECIMAL(2, 1), # number of wins team1 has vs team2
    created timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
