#!/bin/bash
# Database setup without sudo - tries different connection methods

echo "DuckHunt Bot Database Setup (No Sudo)"
echo "====================================="

# Try to connect without password first
echo "Attempting to connect to MariaDB without password..."
mysql -u root -e "SELECT 1;" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✓ Connected without password"
    mysql -u root << 'EOF'
CREATE DATABASE IF NOT EXISTS duckhunt;
DROP USER IF EXISTS 'duckhunt'@'localhost';
CREATE USER 'duckhunt'@'localhost' IDENTIFIED BY 'duckhunt123';
ALTER USER 'duckhunt'@'localhost' IDENTIFIED WITH mysql_native_password BY 'duckhunt123';
GRANT ALL PRIVILEGES ON duckhunt.* TO 'duckhunt'@'localhost';
FLUSH PRIVILEGES;
EOF
else
    echo "✗ Cannot connect without password"
    echo "Please run these commands manually:"
    echo ""
    echo "1. Connect to MariaDB:"
    echo "   mysql -u root -p"
    echo ""
    echo "2. Run these SQL commands:"
    echo "   CREATE DATABASE IF NOT EXISTS duckhunt;"
    echo "   DROP USER IF EXISTS 'duckhunt'@'localhost';"
    echo "   CREATE USER 'duckhunt'@'localhost' IDENTIFIED BY 'duckhunt123';"
    echo "   ALTER USER 'duckhunt'@'localhost' IDENTIFIED WITH mysql_native_password BY 'duckhunt123';"
    echo "   GRANT ALL PRIVILEGES ON duckhunt.* TO 'duckhunt'@'localhost';"
    echo "   FLUSH PRIVILEGES;"
    echo "   exit;"
    echo ""
    echo "3. Then run: mysql -u duckhunt -pduckhunt123 duckhunt < schema.sql"
    echo "4. Then run: python3 test_sql.py"
    exit 1
fi

echo "Creating database tables..."
mysql -u duckhunt -pduckhunt123 duckhunt < schema.sql

if [ $? -eq 0 ]; then
    echo "✓ Database tables created successfully"
    echo "Testing SQL backend..."
    python3 test_sql.py
else
    echo "✗ Failed to create database tables"
    exit 1
fi
