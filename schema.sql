-- DuckHunt Bot Database Schema
-- Run this script to create the database structure
-- Updated to match production environment

CREATE DATABASE IF NOT EXISTS duckhunt;
USE duckhunt;

-- Players table - stores basic player information
CREATE TABLE IF NOT EXISTS players (
    id INT(11) AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_username (username)
);

-- Channel stats table - stores per-network/per-channel statistics
CREATE TABLE IF NOT EXISTS channel_stats (
    id INT(11) AUTO_INCREMENT PRIMARY KEY,
    player_id INT(11) NOT NULL,
    network_name VARCHAR(50) NOT NULL,
    channel_name VARCHAR(100) NOT NULL,
    xp INT(11) DEFAULT 0,
    ducks_shot INT(11) DEFAULT 0,
    golden_ducks INT(11) DEFAULT 0,
    misses INT(11) DEFAULT 0,
    accidents INT(11) DEFAULT 0,
    best_time DECIMAL(10,3) DEFAULT NULL,
    total_reaction_time DECIMAL(12,3) DEFAULT 0.000,
    shots_fired INT(11) DEFAULT 0,
    last_duck_time TIMESTAMP NULL,
    wild_fires INT(11) DEFAULT 0,
    confiscated TINYINT(1) DEFAULT 0,
    jammed TINYINT(1) DEFAULT 0,
    sabotaged TINYINT(1) DEFAULT 0,
    ammo INT(11) DEFAULT 6,
    magazines INT(11) DEFAULT 2,
    ap_shots INT(11) DEFAULT 0,
    explosive_shots INT(11) DEFAULT 0,
    bread_uses INT(11) DEFAULT 0,
    befriended_ducks INT(11) DEFAULT 0,
    trigger_lock_until BIGINT(20) DEFAULT 0,
    trigger_lock_uses INT(11) DEFAULT 0,
    grease_until BIGINT(20) DEFAULT 0,
    silencer_until BIGINT(20) DEFAULT 0,
    sunglasses_until BIGINT(20) DEFAULT 0,
    ducks_detector_until BIGINT(20) DEFAULT 0,
    mirror_until BIGINT(20) DEFAULT 0,
    sand_until BIGINT(20) DEFAULT 0,
    soaked_until BIGINT(20) DEFAULT 0,
    life_insurance_until BIGINT(20) DEFAULT 0,
    liability_insurance_until BIGINT(20) DEFAULT 0,
    mag_upgrade_level INT(11) DEFAULT 0,
    mag_capacity_level INT(11) DEFAULT 0,
    magazine_capacity INT(11) DEFAULT 6,
    magazines_max INT(11) DEFAULT 2,
    clover_until DECIMAL(20,3) DEFAULT 0.000,
    clover_bonus INT(11) DEFAULT 0,
    brush_until DECIMAL(20,3) DEFAULT 0.000,
    sight_next_shot TINYINT(1) DEFAULT 0,
    egged TINYINT(1) DEFAULT 0,
    last_egg_time BIGINT(20) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE,
    UNIQUE KEY unique_player_network_channel (player_id, network_name, channel_name),
    INDEX idx_network_channel (network_name, channel_name),
    INDEX idx_xp (xp),
    INDEX idx_ducks_shot (ducks_shot)
);

-- Active ducks table - stores currently active ducks
CREATE TABLE IF NOT EXISTS active_ducks (
    id INT(11) AUTO_INCREMENT PRIMARY KEY,
    network_name VARCHAR(50) NOT NULL,
    channel_name VARCHAR(100) NOT NULL,
    duck_id VARCHAR(100) NOT NULL,
    is_golden TINYINT(1) DEFAULT 0,
    health INT(11) DEFAULT 5,
    spawn_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    hissed TINYINT(1) DEFAULT 0,
    revealed TINYINT(1) DEFAULT 0,
    UNIQUE KEY unique_network_channel_duck (network_name, channel_name, duck_id),
    INDEX idx_network_channel (network_name, channel_name),
    INDEX idx_spawn_time (spawn_time)
);

-- Channel timing table - stores spawn timing data
CREATE TABLE IF NOT EXISTS channel_timing (
    id INT(11) AUTO_INCREMENT PRIMARY KEY,
    network_name VARCHAR(50) NOT NULL,
    channel_name VARCHAR(100) NOT NULL,
    last_spawn BIGINT(20) DEFAULT 0,
    next_spawn BIGINT(20) DEFAULT 0,
    UNIQUE KEY unique_network_channel (network_name, channel_name),
    INDEX idx_network_channel (network_name, channel_name)
);

-- Channel stats backup table - stores backups before clearing
CREATE TABLE IF NOT EXISTS channel_stats_backup (
    id INT(11) AUTO_INCREMENT PRIMARY KEY,
    backup_id VARCHAR(100) NOT NULL,
    player_id INT(11) NOT NULL,
    network_name VARCHAR(50) NOT NULL,
    channel_name VARCHAR(100) NOT NULL,
    xp INT(11) DEFAULT 0,
    ducks_shot INT(11) DEFAULT 0,
    golden_ducks INT(11) DEFAULT 0,
    misses INT(11) DEFAULT 0,
    accidents INT(11) DEFAULT 0,
    best_time DECIMAL(10,3) DEFAULT NULL,
    total_reaction_time DECIMAL(12,3) DEFAULT 0.000,
    shots_fired INT(11) DEFAULT 0,
    last_duck_time TIMESTAMP NULL,
    wild_fires INT(11) DEFAULT 0,
    confiscated TINYINT(1) DEFAULT 0,
    jammed TINYINT(1) DEFAULT 0,
    sabotaged TINYINT(1) DEFAULT 0,
    ammo INT(11) DEFAULT 0,
    magazines INT(11) DEFAULT 0,
    ap_shots INT(11) DEFAULT 0,
    explosive_shots INT(11) DEFAULT 0,
    bread_uses INT(11) DEFAULT 0,
    befriended_ducks INT(11) DEFAULT 0,
    trigger_lock_until BIGINT(20) DEFAULT 0,
    trigger_lock_uses INT(11) DEFAULT 0,
    grease_until BIGINT(20) DEFAULT 0,
    silencer_until BIGINT(20) DEFAULT 0,
    sunglasses_until BIGINT(20) DEFAULT 0,
    ducks_detector_until BIGINT(20) DEFAULT 0,
    mirror_until BIGINT(20) DEFAULT 0,
    sand_until BIGINT(20) DEFAULT 0,
    soaked_until BIGINT(20) DEFAULT 0,
    life_insurance_until BIGINT(20) DEFAULT 0,
    liability_insurance_until BIGINT(20) DEFAULT 0,
    mag_upgrade_level INT(11) DEFAULT 0,
    mag_capacity_level INT(11) DEFAULT 0,
    magazine_capacity INT(11) DEFAULT 0,
    magazines_max INT(11) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    egged TINYINT(1) DEFAULT 0,
    last_egg_time BIGINT(20) DEFAULT 0,
    FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE,
    INDEX idx_backup_id (backup_id),
    INDEX idx_network_channel (network_name, channel_name),
    INDEX idx_created_at (created_at)
);
