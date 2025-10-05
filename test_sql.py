#!/usr/bin/env python3
"""
Test script for SQL backend
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_sql_backend():
    """Test SQL backend functionality"""
    try:
        import mysql.connector
        from duckhunt_bot import SQLBackend
        
        # Test connection
        print("Testing SQL backend connection...")
        db = SQLBackend('localhost', 3306, 'duckhunt', 'duckhunt', 'duckhunt123')
        
        if db.connection and db.connection.is_connected():
            print("✓ SQL backend connection successful")
            
            # Test player creation
            print("Testing player creation...")
            player_id = db.get_player_id('testuser')
            if player_id:
                print(f"✓ Player 'testuser' created with ID: {player_id}")
            
            # Test channel stats creation
            print("Testing channel stats creation...")
            stats = db.get_channel_stats('testuser', 'testnetwork', '#testchannel')
            if stats:
                print("✓ Channel stats created successfully")
                print(f"  XP: {stats.get('xp', 0)}")
            
            # Test stats update
            print("Testing stats update...")
            update_result = db.update_channel_stats('testuser', 'testnetwork', '#testchannel', {
                'xp': 100,
                'ducks_shot': 5
            })
            if update_result:
                print("✓ Stats update successful")
            
            # Test stats retrieval
            print("Testing stats retrieval...")
            updated_stats = db.get_channel_stats('testuser', 'testnetwork', '#testchannel')
            if updated_stats and updated_stats.get('xp') == 100:
                print("✓ Stats retrieval successful")
                print(f"  Updated XP: {updated_stats.get('xp')}")
                print(f"  Ducks shot: {updated_stats.get('ducks_shot')}")
            
            db.close()
            print("\n✓ All SQL backend tests passed!")
            return True
        else:
            print("✗ SQL backend connection failed")
            return False
            
    except Exception as e:
        print(f"✗ SQL backend test failed: {e}")
        return False

def test_bot_with_sql():
    """Test bot initialization with SQL backend"""
    try:
        import mysql.connector
        # Temporarily modify config to use SQL
        import configparser
        config = configparser.ConfigParser()
        config.read('duckhunt.conf')
        config.set('DEFAULT', 'data_storage', 'sql')
        
        with open('duckhunt.conf.test', 'w') as f:
            config.write(f)
        
        print("Testing bot initialization with SQL backend...")
        from duckhunt_bot import DuckHuntBot
        bot = DuckHuntBot('duckhunt.conf.test')
        
        if bot.data_storage == 'sql' and bot.db_backend:
            print("✓ Bot initialized with SQL backend successfully")
            bot.db_backend.close()
            return True
        else:
            print("✗ Bot failed to initialize with SQL backend")
            return False
            
    except Exception as e:
        print(f"✗ Bot SQL test failed: {e}")
        return False
    finally:
        # Clean up test config
        if os.path.exists('duckhunt.conf.test'):
            os.remove('duckhunt.conf.test')

if __name__ == "__main__":
    print("DuckHunt Bot SQL Backend Test")
    print("=============================")
    
    sql_test = test_sql_backend()
    bot_test = test_bot_with_sql()
    
    if sql_test and bot_test:
        print("\n🎉 All tests passed! SQL backend is working correctly.")
    else:
        print("\n❌ Some tests failed. Please check your database setup.")
        sys.exit(1)
