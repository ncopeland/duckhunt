# Duck Hunt IRC Bot v1.0_build51

An advanced IRC bot that hosts Duck Hunt games in IRC channels with full shop system, karma tracking, and multi-network support. Players shoot ducks with `!bang` when they appear!

## How to Play

1. Join the IRC channel where the bot is running
2. Wait for a duck to spawn (announced with `\_O< QUACK`)
3. Type `!bang` to shoot the duck
4. Earn XP and level up by shooting ducks
5. Use `!shop` to buy items with XP
6. Use `!duckstats` to see your stats
7. Use `!topduck` to see leaderboards

## Commands

### Player Commands
- `!bang` - Shoot the current duck
- `!bef` - Befriend the current duck
- `!reload` - Reload your gun
- `!shop [id] [target]` - View purchasable items or buy item (some items require target)
- `!duckstats [player]` - View your statistics or another player's stats
- `!topduck [duck]` - View leaderboard by XP or by ducks killed
- `!lastduck` - Show when you last shot a duck
- `!duckhelp` - Show help

### Admin Commands
- `!spawnduck [count]` - Spawn one or more ducks (up to max_ducks)
- `!spawngold` - Spawn a golden duck
- `!nextduck` - Show next duck spawn ETA (owner only)
- `!join <channel>` - Join a new channel (owner only)
- `!rearm <player>` - Give a player a gun
- `!disarm <player>` - Confiscate a player's gun

## Running the Bot

1. First run creates `duckhunt.conf` with default settings
2. Edit `duckhunt.conf` with your IRC server details (generated defaults shown):
   ```
   [DEFAULT]
   # DuckHunt Configuration - All settings are network-specific

   # Network configurations
   [network:example]
   server = irc.example.net/6667
   ssl = off
   bot_nick = DuckHuntBot,DuckHuntBot2
   channel = #yourchannel
   perform = PRIVMSG nickserv :identify yourpassword ; PRIVMSG YourNick :I am here
   owner = YourNick
   admin = Admin1,Admin2
   min_spawn = 600
   max_spawn = 1800
   gold_ratio = 0.1
   default_xp = 10
   max_ducks = 5
   despawn_time = 700

   # Shop item prices (XP cost) - can be overridden per network
   shop_extra_bullet = 7
   shop_extra_magazine = 20
   shop_ap_ammo = 15
   shop_explosive_ammo = 25
   shop_repurchase_gun = 40
   shop_grease = 8
   shop_sight = 6
   shop_infrared_detector = 15
   shop_silencer = 5
   shop_four_leaf_clover = 13
   shop_sunglasses = 5
   shop_spare_clothes = 7
   shop_brush_for_gun = 7
   shop_mirror = 7
   shop_handful_of_sand = 7
   shop_water_bucket = 10
   shop_sabotage = 14
   shop_life_insurance = 10
   shop_liability_insurance = 5
   shop_piece_of_bread = 50
   shop_ducks_detector = 50
   shop_upgrade_magazine = 200
   shop_extra_magazine = 400
   ```

3. Run the bot:
   ```bash
   # Manual start (exits on restart command)
   python3 duckhunt_bot.py
   
   # Auto-restart wrapper (recommended)
   ./duckhunt_wrapper.sh
   ```

## Features

### Core Gameplay
- **Multiple Ducks**: Up to `max_ducks` per channel (FIFO targeting of oldest)
- **Despawns**: Ducks despawn after `despawn_time` seconds (configurable)
- **Spawning**: Random spawns every `min_spawn`–`max_spawn` seconds per channel
- **XP System**: Base + bonuses; random miss penalties (-1 to -5 XP)
- **Leveling & Stats**: Level-based accuracy, reliability, clip size, magazines
- **Dynamic Ammo**: All HUD lines use level-based clip/mag values; new players start with those capacities
- **Golden Ducks**: 5 HP; worth 50 XP; AP/Explosive ammo do 2 dmg vs golden; revealed on first hit/befriend

### Shop System (23 Items)
- **Ammo & Weapons**: Extra bullets, magazines, AP/Explosive ammo, sights, silencers
- **Protection**: Sunglasses, life/liability insurance, spare clothes
- **Sabotage**: Mirror, sand, water bucket, sabotage (all require target)
- **Upgrades**: Magazine capacity upgrades (5 levels max, dynamic pricing)
- **Consumables**: Bread, grease, brush, four-leaf clover, detectors
- **Target-based Items**: Some items require `!shop <id> <target>` syntax

### Advanced Features
- **Multi-Network Support**: Connect to multiple IRC networks simultaneously
- **Karma System**: Track good/bad actions with karma percentage in stats
- **Accidental Shooting**: Wild fire (50% chance) and ricochet (20% chance) can hit other players
- **Item Interactions**: Complex interactions (mirror vs sunglasses, sand vs brush, etc.)
- **Weighted Loot**: 10% drop chance on kills with historically balanced loot table
- **Colorized Output**: IRC color codes for enhanced visual experience
- **Log Management**: Automatic log file trimming (10MB limit)
- **Async Architecture**: Non-blocking I/O for better performance

### Admin Features
- **Channel Management**: Join new channels, spawn ducks, manage players
- **Player Management**: Rearm/disarm players, clear channel stats
- **Spawn Control**: Manual duck spawning, golden duck spawning
- **Network-Specific**: All settings and permissions are network-specific

## Game Mechanics

### Combat System
- **Spawn**: Random spawns per channel up to `max_ducks`; oldest duck is always targeted
- **Shoot or Befriend**: `!bang` applies accuracy/reliability; `!bef` uses befriending accuracy
- **Miss Penalties**: Random -1 to -5 XP for misses; wild fire adds -2 XP
- **Accidental Shooting**: Wild fire (50% chance) and ricochet (20% chance) can hit other players
- **Insurance**: Life insurance prevents confiscation; liability insurance halves penalties

### Item System
- **Loot on Kill (10%)**: Weighted random loot; common/uncommon/rare/junk; durations mostly 24h
- **Shop Items**: 23 different items with various effects and durations
- **Consumables**: Do not stack; must be used up before buying again; shown in `!duckstats`
- **Upgrades**: Magazine capacity upgrades with dynamic pricing (5 levels max)

### Detection Systems
- **Ducks Detector**: 60s pre-spawn notice while active (24h)
- **Infrared Detector**: `!bang` with no duck is safely locked; limited uses (6 uses/24h)
- **Golden Duck Detection**: Revealed on first hit or befriend attempt

### Leveling & Stats
- **XP System**: Base XP + bonuses; level-based accuracy, reliability, clip size
- **Karma Tracking**: Good/bad actions tracked with karma percentage
- **Promotion/Demotion**: Automatic level change announcements
- **Channel-Specific**: All stats are tracked per channel

## Configuration

The bot uses `duckhunt.conf` for all settings with multi-network support:
- **Network-Specific Settings**: Each network has its own configuration section
- **IRC Connection**: Server, SSL, nickname, channels, perform commands
- **Game Settings**: Spawn timing, XP values, duck limits, despawn times
- **Permissions**: Owner and admin lists per network
- **Shop Prices**: All 23 shop item prices (can be overridden per network)
- **Backward Compatibility**: Falls back to global settings if network-specific not found

## License

GPLv2 (GNU General Public License v2.0)

This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License version 2 as published by the Free Software Foundation.
