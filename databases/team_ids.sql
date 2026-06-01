CREATE TABLE team_ids (
    id VARCHAR(8) PRIMARY KEY,
    season INT,
    team_id INT,
    manager_id VARCHAR(50),
    created timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
