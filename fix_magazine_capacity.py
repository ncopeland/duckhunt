#!/usr/bin/env python3
"""
Fix magazine_capacity for all players in the database.
This script calculates the correct magazine_capacity based on each player's XP level.
"""

import mysql.connector

def get_level_properties(xp: int) -> dict:
    """Return level properties based on XP."""
    thresholds = [
        (-5, 0, 55, 85, 6, 1,  -1, -1, -4),
        (-4, 1, 55, 85, 6, 2,  -1, -1, -4),
        (20, 2, 56, 86, 6, 2,  -1, -1, -4),
        (50, 3, 57, 87, 6, 2,  -1, -1, -4),
        (90, 4, 58, 88, 6, 2,  -1, -1, -4),
        (140,5, 59, 89, 6, 2,  -1, -1, -4),
        (200,6, 60, 90, 6, 2,  -1, -1, -4),
        (270,7, 65, 93, 4, 3,  -1, -1, -4),
        (350,8, 67, 93, 4, 3,  -1, -1, -4),
        (440,9, 69, 93, 4, 3,  -1, -1, -4),
        (540,10,71, 94, 4, 3,  -1, -2, -6),
        (650,11,73, 94, 4, 3,  -1, -2, -6),
        (770,12,73, 94, 4, 3,  -1, -2, -6),
        (900,13,74, 95, 4, 3,  -1, -2, -6),
        (1040,14,74,95, 4, 3,  -1, -2, -6),
        (1190,15,75,95, 4, 3,  -1, -2, -6),
        (1350,16,80,97, 2, 4,  -1, -2, -6),
        (1520,17,81,97, 2, 4,  -1, -2, -6),
        (1700,18,81,97, 2, 4,  -1, -2, -6),
        (1890,19,82,97, 2, 4,  -1, -2, -6),
        (2090,20,82,97, 2, 4,  -3, -5, -10),
        (2300,21,83,98, 2, 4,  -3, -5, -10),
        (2520,22,83,98, 2, 4,  -3, -5, -10),
        (2750,23,84,98, 2, 4,  -3, -5, -10),
        (2990,24,84,98, 2, 4,  -3, -5, -10),
        (3240,25,85,98, 2, 4,  -3, -5, -10),
        (3500,26,90,99, 1, 5,  -3, -5, -10),
        (3770,27,91,99, 1, 5,  -3, -5, -10),
        (4050,28,91,99, 1, 5,  -3, -5, -10),
        (4340,29,92,99, 1, 5,  -3, -5, -10),
        (4640,30,92,99, 1, 5,  -5, -8, -20),
        (4950,31,93,99, 1, 5,  -5, -8, -20),
        (5270,32,93,99, 1, 5,  -5, -8, -20),
        (5600,33,94,99, 1, 5,  -5, -8, -20),
        (5940,34,94,99, 1, 5,  -5, -8, -20),
        (6290,35,95,99, 1, 5,  -5, -8, -20),
        (6650,36,95,99, 1, 5,  -5, -8, -20),
        (7020,37,96,99, 1, 5,  -5, -8, -20),
        (7400,38,96,99, 1, 5,  -5, -8, -20),
        (7790,39,97,99, 1, 5,  -5, -8, -20),
        (8200,40,97,99, 1, 5,  -5, -8, -20),
    ]
    # Pick the highest threshold <= xp
    chosen = thresholds[0]
    for t in thresholds:
        if xp >= t[0]:
            chosen = t
    _, level, acc, rel, clip, clips, misspen, wildpen, accpen = chosen
    return {
        'magazine_capacity': clip,
        'magazines_max': clips,
    }

def main():
    # Connect to database
    conn = mysql.connector.connect(
        host='localhost',
        port=3306,
        database='duckhunt',
        user='duckhunt',
        password='duckhunt123',
        autocommit=True
    )
    
    cursor = conn.cursor(dictionary=True)
    
    # Get all players with magazine_capacity = 0
    cursor.execute("""
        SELECT p.id, p.username, cs.id as cs_id, cs.xp, cs.mag_upgrade_level, cs.mag_capacity_level,
               cs.magazine_capacity, cs.magazines_max
        FROM players p
        JOIN channel_stats cs ON p.id = cs.player_id
        WHERE cs.magazine_capacity = 0
    """)
    
    players = cursor.fetchall()
    
    print(f"Found {len(players)} player records with magazine_capacity = 0")
    
    fixed_count = 0
    for player in players:
        xp = player['xp']
        props = get_level_properties(int(xp))
        
        # Apply upgrade bonuses
        base_magazine_capacity = props['magazine_capacity']
        base_magazines_max = props['magazines_max']
        
        mag_upgrade_level = player['mag_upgrade_level'] or 0
        mag_capacity_level = player['mag_capacity_level'] or 0
        
        correct_magazine_capacity = base_magazine_capacity + mag_upgrade_level
        correct_magazines_max = base_magazines_max + mag_capacity_level
        
        # Update the record
        cursor.execute("""
            UPDATE channel_stats
            SET magazine_capacity = %s, magazines_max = %s
            WHERE id = %s
        """, (correct_magazine_capacity, correct_magazines_max, player['cs_id']))
        
        print(f"Fixed {player['username']}: XP={xp}, mag_cap: 0 -> {correct_magazine_capacity}, mags_max: {player['magazines_max']} -> {correct_magazines_max}")
        fixed_count += 1
    
    cursor.close()
    conn.close()
    
    print(f"\nFixed {fixed_count} player records")

if __name__ == "__main__":
    main()

