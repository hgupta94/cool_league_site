CREATE TABLE switcher (
    id VARCHAR(255) PRIMARY KEY,
    season INT,
    week INT,
    team VARCHAR(255),
    schedule_of VARCHAR(255),
    result DECIMAL(2, 1),
    created timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
