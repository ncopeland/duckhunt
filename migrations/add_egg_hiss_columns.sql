-- Migration: Add egg and hiss mechanics columns
-- Run this script to add the new fields for egg command and hissed ducks

USE duckhunt;

-- Add new columns to channel_stats table
ALTER TABLE channel_stats 
ADD COLUMN IF NOT EXISTS egged BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS last_egg_time BIGINT DEFAULT 0;

-- Add new columns to active_ducks table for hissed state
ALTER TABLE active_ducks 
ADD COLUMN IF NOT EXISTS hissed BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS revealed BOOLEAN DEFAULT FALSE;

-- Add new columns to channel_stats_backup table (mirror the main table)
ALTER TABLE channel_stats_backup 
ADD COLUMN IF NOT EXISTS egged BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS last_egg_time BIGINT DEFAULT 0;
