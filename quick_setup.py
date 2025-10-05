#!/usr/bin/env python3
"""
Quick setup script - run this after you've created the database manually
"""

import os
import sys

def main():
    print("DuckHunt Bot Quick Setup")
    print("========================")
    
    # Check if database exists and is accessible
    try:
        import mysql.connector
        connection = mysql.connector.connect(
            host='localhost',
            user='duckhunt',
            password='duckhunt123',
            database='duckhunt'
        )
        print("✓ Database connection successful")
        connection.close()
    except Exception as e:
        print(f"✗ Cannot connect to database: {e}")
        print("\nPlease run these commands first:")
        print("1. mysql -u root -p")
        print("2. CREATE DATABASE IF NOT EXISTS duckhunt;")
        print("3. CREATE USER 'duckhunt'@'localhost' IDENTIFIED BY 'duckhunt123';")
        print("4. GRANT ALL PRIVILEGES ON duckhunt.* TO 'duckhunt'@'localhost';")
        print("5. FLUSH PRIVILEGES;")
        print("6. exit;")
        print("7. mysql -u duckhunt -pduckhunt123 duckhunt < schema.sql")
        return False
    
    # Test the SQL backend
    print("\nTesting SQL backend...")
    try:
        from duckhunt_bot import test_sql_backend
        if test_sql_backend():
            print("✓ SQL backend test passed")
        else:
            print("✗ SQL backend test failed")
            return False
    except Exception as e:
        print(f"✗ SQL backend test error: {e}")
        return False
    
    # Migrate existing data if it exists
    if os.path.exists('duckhunt.data'):
        print("\nMigrating existing JSON data to SQL...")
        try:
            from duckhunt_bot import migrate_json_to_sql
            sql_config = {
                'host': 'localhost',
                'port': 3306,
                'database': 'duckhunt',
                'user': 'duckhunt',
                'password': 'duckhunt123'
            }
            if migrate_json_to_sql('duckhunt.data', sql_config):
                print("✓ Data migration successful")
            else:
                print("✗ Data migration failed")
                return False
        except Exception as e:
            print(f"✗ Data migration error: {e}")
            return False
    else:
        print("\nNo existing JSON data found - starting fresh")
    
    # Update config to use SQL
    print("\nUpdating configuration to use SQL backend...")
    try:
        import configparser
        config = configparser.ConfigParser()
        config.read('duckhunt.conf')
        config.set('DEFAULT', 'data_storage', 'sql')
        
        with open('duckhunt.conf', 'w') as f:
            config.write(f)
        
        print("✓ Configuration updated")
    except Exception as e:
        print(f"✗ Configuration update failed: {e}")
        return False
    
    print("\n🎉 Setup completed successfully!")
    print("The bot is now configured to use the SQL backend.")
    print("You can start it with: python3 duckhunt_bot.py")
    
    return True

if __name__ == "__main__":
    if main():
        sys.exit(0)
    else:
        sys.exit(1)
