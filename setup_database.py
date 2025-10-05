#!/usr/bin/env python3
"""
Database setup script for DuckHunt Bot
This script creates the database schema and migrates existing JSON data
"""

import os
import sys
import mysql.connector
from mysql.connector import Error

def setup_database():
    """Create database and tables"""
    try:
        # Connect to MySQL/MariaDB as root
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password=input("Enter MySQL root password: ")
        )
        
        cursor = connection.cursor()
        
        # Create database
        cursor.execute("CREATE DATABASE IF NOT EXISTS duckhunt")
        print("Database 'duckhunt' created/verified")
        
        # Create user
        cursor.execute("CREATE USER IF NOT EXISTS 'duckhunt'@'localhost' IDENTIFIED BY 'duckhunt123'")
        cursor.execute("GRANT ALL PRIVILEGES ON duckhunt.* TO 'duckhunt'@'localhost'")
        cursor.execute("FLUSH PRIVILEGES")
        print("User 'duckhunt' created/verified")
        
        # Use the duckhunt database
        cursor.execute("USE duckhunt")
        
        # Create tables from schema.sql
        schema_file = "schema.sql"
        if os.path.exists(schema_file):
            with open(schema_file, 'r') as f:
                schema_sql = f.read()
            
            # Execute schema (split by semicolons)
            for statement in schema_sql.split(';'):
                statement = statement.strip()
                if statement and not statement.startswith('--'):
                    try:
                        cursor.execute(statement)
                        print(f"Executed: {statement[:50]}...")
                    except Error as e:
                        if "already exists" not in str(e):
                            print(f"Warning: {e}")
        
        connection.commit()
        cursor.close()
        connection.close()
        
        print("Database setup completed successfully!")
        return True
        
    except Error as e:
        print(f"Database setup failed: {e}")
        return False

if __name__ == "__main__":
    print("DuckHunt Bot Database Setup")
    print("==========================")
    
    if setup_database():
        print("\nDatabase is ready!")
        print("You can now:")
        print("1. Change 'data_storage = sql' in duckhunt.conf")
        print("2. Run the bot to test SQL backend")
        print("3. Use migrate_json_to_sql() function to migrate existing data")
    else:
        print("\nDatabase setup failed. Please check your MySQL/MariaDB installation.")
        sys.exit(1)
