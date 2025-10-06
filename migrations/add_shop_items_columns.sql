-- Migration: Add missing shop item columns to channel_stats table
-- Date: 2025-10-06
-- Description: Adds columns for clover, brush, and sight shop items

ALTER TABLE channel_stats 
ADD COLUMN IF NOT EXISTS clover_until DECIMAL(20,3) DEFAULT 0,
ADD COLUMN IF NOT EXISTS clover_bonus INT DEFAULT 0,
ADD COLUMN IF NOT EXISTS brush_until DECIMAL(20,3) DEFAULT 0,
ADD COLUMN IF NOT EXISTS sight_next_shot TINYINT(1) DEFAULT 0;

-- Note: trigger_lock_until and trigger_lock_uses already exist in the schema
-- They are used by shop item #8 (Trigger Lock, formerly called Infrared Detector)

