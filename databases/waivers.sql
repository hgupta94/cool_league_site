CREATE TABLE waivers (
    id INT PRIMARY KEY AUTO_INCREMENT,
    season INT,
    week INT,
    team INT,
    bid INT,
    added INT,
    dropped INT,
    completed DATE,
    created timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
