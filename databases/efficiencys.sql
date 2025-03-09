CREATE TABLE efficiency (
    id VARCHAR(255) PRIMARY KEY,
    season INT,
    week INT,
    team VARCHAR(255),
    act_score FLOAT(6, 2),
    act_proj FLOAT(6, 2),
    best_projected_act FLOAT(6, 2),
    best_projected_proj FLOAT(6, 2),
    optimal_lineup_act FLOAT(6, 2),
    optimal_lineup_proj FLOAT(6, 2),
    created timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
