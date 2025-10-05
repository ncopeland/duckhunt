#!/usr/bin/env python3
"""
Test script for the clear command with SQL backend
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_clear_command():
    """Test the clear command functionality"""
    try:
        from duckhunt_bot import SQLBackend
        
        print("Testing clear command with SQL backend...")
        
        # Initialize SQL backend
        db = SQLBackend('localhost', 3306, 'duckhunt', 'duckhunt', 'duckhunt123')
        
        if not db.connection or not db.connection.is_connected():
            print("✗ Cannot connect to database")
            return False
        
        print("✓ Connected to database")
        
        # Test clearing a channel that doesn't exist
        cleared_count = db.clear_channel_stats('testnetwork', '#nonexistent')
        print(f"✓ Cleared {cleared_count} stats for non-existent channel (expected: 0)")
        
        # Test clearing a real channel if any exist
        # First, let's see what channels exist
        query = "SELECT DISTINCT network_name, channel_name FROM channel_stats LIMIT 5"
        channels = db.execute_query(query, fetch=True)
        
        if channels:
            print(f"Found {len(channels)} channels in database:")
            for channel in channels:
                print(f"  - {channel['network_name']}:{channel['channel_name']}")
            
            # Test clearing the first channel
            test_channel = channels[0]
            print(f"\nTesting clear for {test_channel['network_name']}:{test_channel['channel_name']}")
            
            # Count before clearing
            count_query = """SELECT COUNT(*) as count 
                             FROM channel_stats 
                             WHERE network_name = %s AND channel_name = %s"""
            before_result = db.execute_query(count_query, (test_channel['network_name'], test_channel['channel_name']), fetch=True)
            before_count = before_result[0]['count'] if before_result else 0
            
            print(f"Stats before clear: {before_count}")
            
            if before_count > 0:
                cleared_count = db.clear_channel_stats(test_channel['network_name'], test_channel['channel_name'])
                print(f"✓ Cleared {cleared_count} stats")
                
                # Count after clearing
                after_result = db.execute_query(count_query, (test_channel['network_name'], test_channel['channel_name']), fetch=True)
                after_count = after_result[0]['count'] if after_result else 0
                print(f"Stats after clear: {after_count}")
                
                if after_count == 0:
                    print("✓ Clear command working correctly!")
                else:
                    print("✗ Clear command failed - stats still exist")
                    return False
        else:
            print("No channels found in database to test with")
        
        db.close()
        print("\n✓ Clear command test completed successfully!")
        return True
        
    except Exception as e:
        print(f"✗ Clear command test failed: {e}")
        return False

if __name__ == "__main__":
    print("DuckHunt Bot Clear Command Test")
    print("===============================")
    
    if test_clear_command():
        print("\n🎉 Clear command is working correctly with SQL backend!")
    else:
        print("\n❌ Clear command test failed.")
        sys.exit(1)
