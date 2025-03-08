CREATE TABLE standings_2018 (
    id VARCHAR(255) PRIMARY KEY,
    season INT,
    week INT,
    `rank` INT,
    team VARCHAR(255),
    record VARCHAR(255),
    win_perc VARCHAR(255),
    total_pf VARCHAR(255),
    wb4 VARCHAR(255),
    created timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
