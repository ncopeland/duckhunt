#!/usr/bin/env python3
"""
Data migration script for DuckHunt Bot
Migrates existing JSON data to SQL database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from duckhunt_bot import migrate_json_to_sql

def main():
    print("DuckHunt Bot Data Migration")
    print("==========================")
    
    json_file = "duckhunt.data"
    if not os.path.exists(json_file):
        print(f"Error: {json_file} not found!")
        return False
    
    print(f"Found JSON data file: {json_file}")
    
    # SQL configuration
    sql_config = {
        'host': 'localhost',
        'port': 3306,
        'database': 'duckhunt',
        'user': 'duckhunt',
        'password': 'duckhunt123'
    }
    
    print("Starting migration...")
    success = migrate_json_to_sql(json_file, sql_config)
    
    if success:
        print("\nMigration completed successfully!")
        print("You can now switch to SQL backend by changing 'data_storage = sql' in duckhunt.conf")
        print("The original JSON file is preserved as backup.")
    else:
        print("\nMigration failed. Please check the database connection and try again.")
    
    return success

if __name__ == "__main__":
    main()
