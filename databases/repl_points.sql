CREATE TABLE repl_points (
    id VARCHAR(20) PRIMARY KEY,
    season INT,
    week INT,
    position_id INT,
    position VARCHAR(4),
    points DECIMAL(4, 2),
    created timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
