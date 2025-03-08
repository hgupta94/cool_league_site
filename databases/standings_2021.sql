CREATE TABLE standings_2021 (
    id VARCHAR(255) PRIMARY KEY,
    season INT,
    week INT,
    rank INT,
    team VARCHAR(255),
    win_perc VARCHAR(255),
    m_record VARCHAR(255),
    total_pf VARCHAR(255),
    ov_record VARCHAR(255),
    thw_record VARCHAR(255),
    wb2 VARCHAR(255),
    wb5 VARCHAR(255),
    pb6 VARCHAR(255),
    created timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
