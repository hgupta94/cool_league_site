CREATE TABLE matchup_results (
    id VARCHAR(255) PRIMARY KEY,
    opponent INT,
    m_result DECIMAL,
    th_result DECIMAL,
    points DECIMAL,
    created timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
