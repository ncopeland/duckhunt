#!/usr/bin/env python3
"""
Debug script for backup system
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def debug_backup_system():
    """Debug the backup system"""
    try:
        from duckhunt_bot import SQLBackend
        
        print("Debugging backup system...")
        
        # Initialize SQL backend
        db = SQLBackend('localhost', 3306, 'duckhunt', 'duckhunt', 'duckhunt123')
        
        if not db.connection or not db.connection.is_connected():
            print("✗ Cannot connect to database")
            return False
        
        print("✓ Connected to database")
        
        # Test network and channel
        test_network = 'testnetwork'
        test_channel = '#testchannel'
        
        # Check what's in the channel_stats table
        print(f"\n1. Checking existing channel stats for {test_network}:{test_channel}")
        query = """SELECT * FROM channel_stats WHERE network_name = %s AND channel_name = %s"""
        existing_stats = db.execute_query(query, (test_network, test_channel), fetch=True)
        
        if existing_stats:
            print(f"✓ Found {len(existing_stats)} existing records:")
            for stat in existing_stats:
                print(f"  Player ID: {stat['player_id']}, XP: {stat['xp']}, Ducks: {stat['ducks_shot']}")
        else:
            print("✗ No existing channel stats found")
        
        # Check all channel stats
        print(f"\n2. Checking all channel stats in database")
        all_query = "SELECT network_name, channel_name, player_id, xp, ducks_shot FROM channel_stats LIMIT 10"
        all_stats = db.execute_query(all_query, fetch=True)
        
        if all_stats:
            print(f"✓ Found {len(all_stats)} total records in channel_stats:")
            for stat in all_stats:
                print(f"  {stat['network_name']}:{stat['channel_name']} - Player {stat['player_id']}: XP={stat['xp']}, Ducks={stat['ducks_shot']}")
        else:
            print("✗ No records in channel_stats table")
        
        # Check players table
        print(f"\n3. Checking players table")
        players_query = "SELECT id, username FROM players LIMIT 10"
        players = db.execute_query(players_query, fetch=True)
        
        if players:
            print(f"✓ Found {len(players)} players:")
            for player in players:
                print(f"  ID: {player['id']}, Username: {player['username']}")
        else:
            print("✗ No players in database")
        
        # Try to create test data if none exists
        if not existing_stats:
            print(f"\n4. Creating test data")
            player_id = db.get_player_id('TestPlayer')
            print(f"✓ Test player ID: {player_id}")
            
            # Create test channel stats using direct SQL
            test_stats = {
                'xp': 100,
                'ducks_shot': 5,
                'golden_ducks': 1,
                'misses': 2,
                'best_time': 2.5,
                'ammo': 6,
                'magazines': 2
            }
            
            # Build INSERT query
            columns = ['player_id', 'network_name', 'channel_name'] + list(test_stats.keys())
            values = [player_id, test_network, test_channel] + list(test_stats.values())
            
            insert_query = f"""INSERT INTO channel_stats ({', '.join(columns)}) VALUES ({', '.join(['%s'] * len(values))}) 
                               ON DUPLICATE KEY UPDATE 
                               {', '.join([f"{k} = VALUES({k})" for k in test_stats.keys()])}"""
            
            success = db.execute_query(insert_query, values)
            if success:
                print("✓ Test channel stats created directly")
            else:
                print("✗ Failed to create test channel stats directly")
        
        # Now test backup again
        print(f"\n5. Testing backup again")
        backup_id, backup_count = db.backup_channel_stats(test_network, test_channel)
        print(f"✓ Backup created: {backup_id} ({backup_count} records)")
        
        # Check backup table
        print(f"\n6. Checking backup table")
        backup_query = "SELECT backup_id, player_id, xp, ducks_shot FROM channel_stats_backup WHERE backup_id = %s"
        backup_records = db.execute_query(backup_query, (backup_id,), fetch=True)
        
        if backup_records:
            print(f"✓ Found {len(backup_records)} backup records:")
            for record in backup_records:
                print(f"  Backup ID: {record['backup_id']}, Player ID: {record['player_id']}, XP: {record['xp']}, Ducks: {record['ducks_shot']}")
        else:
            print("✗ No backup records found")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"✗ Debug failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("DuckHunt Bot Backup System Debug")
    print("===============================")
    
    debug_backup_system()
