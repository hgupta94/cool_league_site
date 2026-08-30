CREATE TABLE trades (
    id INT PRIMARY KEY AUTO_INCREMENT,
    season INT,
    week INT,
    trade_id CHAR(36),
    team_from INT,
    team_to INT,
    player INT,
    faab INT,
    completed DATE,
    created timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
