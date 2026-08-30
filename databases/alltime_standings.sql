CREATE TABLE alltime_standings (
    team VARCHAR(4) PRIMARY KEY,
    seasons INT,
    playoffs INT,
    overall_rec VARCHAR(10),
    win_perc DECIMAL(4, 3),
    matchup_rec VARCHAR(10),
    tophalf_rec VARCHAR(10),
    points DECIMAL(10, 2),
    created timestamp DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
