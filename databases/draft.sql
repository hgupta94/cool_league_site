CREATE TABLE draft (
    id VARCHAR(20) PRIMARY KEY,
    season INT,
    draft_type VARCHAR(20),
    round INT,
    round_pick INT,
    pick INT,
    bid INT,
    nom_team INT,
    pick_team INT,
    player_id INT,
    player_name VARCHAR(50),
    player_position VARCHAR(4),
    created timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
