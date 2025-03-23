CREATE TABLE switcher (
    id VARCHAR(24) PRIMARY KEY,
    season INT,
    week INT,
    team VARCHAR(6),
    schedule_of VARCHAR(6),
    result DECIMAL(2, 1),
    created timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
