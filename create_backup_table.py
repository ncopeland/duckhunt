#!/usr/bin/env python3
"""
Script to create the backup table in the database
"""

import mysql.connector
from mysql.connector import Error

def create_backup_table():
    """Create the channel_stats_backup table"""
    try:
        # Connect to database
        connection = mysql.connector.connect(
            host='localhost',
            port=3306,
            database='duckhunt',
            user='duckhunt',
            password='duckhunt123'
        )
        
        if connection.is_connected():
            cursor = connection.cursor()
            
            # Create backup table
            backup_table_sql = """
            CREATE TABLE IF NOT EXISTS channel_stats_backup (
                id INT AUTO_INCREMENT PRIMARY KEY,
                backup_id VARCHAR(100) NOT NULL,
                player_id INT NOT NULL,
                network_name VARCHAR(50) NOT NULL,
                channel_name VARCHAR(100) NOT NULL,
                xp INT DEFAULT 0,
                ducks_shot INT DEFAULT 0,
                golden_ducks INT DEFAULT 0,
                misses INT DEFAULT 0,
                accidents INT DEFAULT 0,
                best_time DECIMAL(10,3) DEFAULT NULL,
                total_reaction_time DECIMAL(12,3) DEFAULT 0.0,
                shots_fired INT DEFAULT 0,
                last_duck_time TIMESTAMP NULL,
                wild_fires INT DEFAULT 0,
                confiscated BOOLEAN DEFAULT FALSE,
                jammed BOOLEAN DEFAULT FALSE,
                sabotaged BOOLEAN DEFAULT FALSE,
                ammo INT DEFAULT 0,
                magazines INT DEFAULT 0,
                ap_shots INT DEFAULT 0,
                explosive_shots INT DEFAULT 0,
                bread_uses INT DEFAULT 0,
                befriended_ducks INT DEFAULT 0,
                trigger_lock_until BIGINT DEFAULT 0,
                trigger_lock_uses INT DEFAULT 0,
                grease_until BIGINT DEFAULT 0,
                silencer_until BIGINT DEFAULT 0,
                sunglasses_until BIGINT DEFAULT 0,
                ducks_detector_until BIGINT DEFAULT 0,
                mirror_until BIGINT DEFAULT 0,
                sand_until BIGINT DEFAULT 0,
                soaked_until BIGINT DEFAULT 0,
                life_insurance_until BIGINT DEFAULT 0,
                liability_insurance_until BIGINT DEFAULT 0,
                mag_upgrade_level INT DEFAULT 0,
                mag_capacity_level INT DEFAULT 0,
                magazine_capacity INT DEFAULT 0,
                magazines_max INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE,
                INDEX idx_backup_id (backup_id),
                INDEX idx_network_channel (network_name, channel_name),
                INDEX idx_created_at (created_at)
            )
            """
            
            cursor.execute(backup_table_sql)
            connection.commit()
            
            print("✓ Backup table created successfully!")
            
            # Check if table exists
            cursor.execute("SHOW TABLES LIKE 'channel_stats_backup'")
            result = cursor.fetchone()
            if result:
                print("✓ Backup table verified in database")
            else:
                print("✗ Backup table not found after creation")
                return False
            
            cursor.close()
            connection.close()
            return True
            
    except Error as e:
        print(f"✗ Database error: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    print("Creating DuckHunt Bot Backup Table")
    print("==================================")
    
    if create_backup_table():
        print("\n🎉 Backup table created successfully!")
    else:
        print("\n❌ Failed to create backup table.")
        exit(1)
