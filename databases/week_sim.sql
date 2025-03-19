CREATE TABLE week_sim (
    id VARCHAR(255) PRIMARY KEY,
    avg_score DECIMAL(6, 2),
    p_win DECIMAL(4, 1),
    p_tophalf DECIMAL(4, 1),
    p_highest DECIMAL(4, 1),
    p_lowest DECIMAL(4, 1),
    created timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
