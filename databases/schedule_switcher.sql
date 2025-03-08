CREATE TABLE switcher (
    id VARCHAR(255) PRIMARY KEY,
    season INT,
    week INT,
    team VARCHAR(255),
    schedul_of VARCHAR(255),
    result DECIMAL(),
    created timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
