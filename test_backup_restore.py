#!/usr/bin/env python3
"""
Test script for the backup/restore system
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_backup_restore_system():
    """Test the complete backup/restore functionality"""
    try:
        from duckhunt_bot import SQLBackend
        
        print("Testing backup/restore system...")
        
        # Initialize SQL backend
        db = SQLBackend('localhost', 3306, 'duckhunt', 'duckhunt', 'duckhunt123')
        
        if not db.connection or not db.connection.is_connected():
            print("✗ Cannot connect to database")
            return False
        
        print("✓ Connected to database")
        
        # Test network and channel
        test_network = 'testnetwork'
        test_channel = '#testchannel'
        
        # First, create some test data if it doesn't exist
        print(f"\n1. Creating test data for {test_network}:{test_channel}")
        
        # Get or create a test player
        player_id = db.get_player_id('TestPlayer')
        print(f"✓ Test player ID: {player_id}")
        
        # Create test channel stats
        test_stats = {
            'xp': 100,
            'ducks_shot': 5,
            'golden_ducks': 1,
            'misses': 2,
            'best_time': 2.5,
            'ammo': 6,
            'magazines': 2
        }
        
        # Update channel stats
        success = db.update_channel_stats(player_id, test_network, test_channel, test_stats)
        if success:
            print("✓ Test channel stats created")
        else:
            print("✗ Failed to create test channel stats")
            return False
        
        # 2. Test backup functionality
        print(f"\n2. Testing backup for {test_network}:{test_channel}")
        backup_id, backup_count = db.backup_channel_stats(test_network, test_channel)
        print(f"✓ Backup created: {backup_id} ({backup_count} records)")
        
        if backup_count == 0:
            print("✗ No records backed up")
            return False
        
        # 3. Test clear functionality (with backup)
        print(f"\n3. Testing clear with backup for {test_network}:{test_channel}")
        cleared_count, returned_backup_id = db.clear_channel_stats(test_network, test_channel, backup=True)
        print(f"✓ Cleared {cleared_count} records (backup: {returned_backup_id})")
        
        if cleared_count == 0:
            print("✗ No records cleared")
            return False
        
        if returned_backup_id != backup_id:
            print(f"⚠ Warning: Backup IDs don't match ({backup_id} vs {returned_backup_id})")
        
        # 4. Verify data is cleared
        print(f"\n4. Verifying data is cleared")
        remaining_stats = db.get_channel_stats(player_id, test_network, test_channel)
        if remaining_stats and remaining_stats.get('xp', 0) > 0:
            print(f"✗ Data still exists after clear: {remaining_stats}")
            return False
        else:
            print("✓ Data successfully cleared")
        
        # 5. Test restore functionality
        print(f"\n5. Testing restore from backup {backup_id}")
        restored_count = db.restore_channel_stats(backup_id)
        print(f"✓ Restored {restored_count} records")
        
        if restored_count != backup_count:
            print(f"⚠ Warning: Restored count ({restored_count}) doesn't match backup count ({backup_count})")
        
        # 6. Verify data is restored
        print(f"\n6. Verifying data is restored")
        restored_stats = db.get_channel_stats(player_id, test_network, test_channel)
        if restored_stats and restored_stats.get('xp') == test_stats['xp']:
            print("✓ Data successfully restored")
            print(f"  Restored stats: XP={restored_stats.get('xp')}, Ducks={restored_stats.get('ducks_shot')}")
        else:
            print(f"✗ Data not properly restored: {restored_stats}")
            return False
        
        # 7. Test list backups functionality
        print(f"\n7. Testing list backups")
        backups = db.list_backups(test_network, test_channel)
        if backups and len(backups) > 0:
            print(f"✓ Found {len(backups)} backup(s) for {test_network}:{test_channel}")
            for backup in backups:
                print(f"  - {backup['backup_id']} ({backup['created_at']}, {backup['player_count']} players)")
        else:
            print("✗ No backups found")
            return False
        
        # 8. Test restore with invalid backup ID
        print(f"\n8. Testing restore with invalid backup ID")
        invalid_restore = db.restore_channel_stats('invalid_backup_id')
        if invalid_restore == 0:
            print("✓ Invalid backup ID correctly handled")
        else:
            print(f"✗ Invalid backup ID returned {invalid_restore} instead of 0")
            return False
        
        db.close()
        print("\n✓ Backup/restore system test completed successfully!")
        return True
        
    except Exception as e:
        print(f"✗ Backup/restore test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("DuckHunt Bot Backup/Restore System Test")
    print("=======================================")
    
    if test_backup_restore_system():
        print("\n🎉 Backup/restore system is working correctly!")
    else:
        print("\n❌ Backup/restore system test failed.")
        sys.exit(1)
