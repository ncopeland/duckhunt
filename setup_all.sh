#!/bin/bash
# Complete database setup script for DuckHunt Bot

echo "DuckHunt Bot Database Setup"
echo "=========================="

# Check if MariaDB is running
if ! systemctl is-active --quiet mariadb; then
    echo "Starting MariaDB service..."
    sudo systemctl start mariadb
fi

echo "Creating database and user..."

# Create database and user (this will prompt for root password)
sudo mysql << 'EOF'
CREATE DATABASE IF NOT EXISTS duckhunt;
DROP USER IF EXISTS 'duckhunt'@'localhost';
CREATE USER 'duckhunt'@'localhost' IDENTIFIED BY 'duckhunt123';
GRANT ALL PRIVILEGES ON duckhunt.* TO 'duckhunt'@'localhost';
FLUSH PRIVILEGES;
EOF

if [ $? -eq 0 ]; then
    echo "✓ Database and user created successfully"
else
    echo "✗ Failed to create database and user"
    exit 1
fi

echo "Creating database tables..."

# Create tables
mysql -u duckhunt -pduckhunt123 duckhunt < schema.sql

if [ $? -eq 0 ]; then
    echo "✓ Database tables created successfully"
else
    echo "✗ Failed to create database tables"
    exit 1
fi

echo "Testing SQL backend..."

# Test the setup
python3 test_sql.py

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Database setup completed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Migrate existing data: python3 migrate_data.py"
    echo "2. Edit duckhunt.conf and change 'data_storage = sql'"
    echo "3. Start the bot: python3 duckhunt_bot.py"
else
    echo "✗ Database setup test failed"
    exit 1
fi
