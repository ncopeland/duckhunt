# Duck Hunt IRC Bot v1.0_build36

An IRC bot that hosts Duck Hunt games in IRC channels. Players shoot ducks with `!bang` when they appear!

## How to Play

1. Join the IRC channel where the bot is running
2. Wait for a duck to spawn (announced with `\_O< QUACK`)
3. Type `!bang` to shoot the duck
4. Earn XP and level up by shooting ducks
5. Use `!shop` to buy items with XP
6. Use `!duckstats` to see your stats
7. Use `!topduck` to see leaderboards

## Commands

- `!bang` - Shoot the current duck
- `!bef` - Befriend the current duck
- `!reload` - Reload your gun
- `!shop` - View purchasable items
- `!duckstats` - View your statistics
- `!topduck` - View leaderboard
- `!lastduck` - Show when you last shot a duck
- `!duckhelp` - Show help
- `!spawnduck [count]` - Admin: Spawn one or more ducks (up to max_ducks)
- `!spawngold` - Admin: Spawn a golden duck

## Running the Bot

1. First run creates `duckhunt.conf` with default settings
2. Edit `duckhunt.conf` with your IRC server details (generated defaults shown):
   ```
   [DEFAULT]
   server = irc.rizon.net/6667
   ssl = off
   bot_nick = DuckHuntBot,DuckHuntBot2
   channel = #yourchannel,#anotherchannel
   perform = PRIVMSG YourNick :I am here
   owner = YourNick
   admin = Admin1,Admin2
   min_spawn = 600
   max_spawn = 1800
   gold_ratio = 0.1
   default_xp = 10
   max_ducks = 5
   despawn_time = 700

   # Shop item prices
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
   ```

3. Run the bot:
   ```bash
   # Manual start (exits on restart command)
   python3 duckhunt_bot.py
   
   # Auto-restart wrapper (recommended)
   ./duckhunt_wrapper.sh
   ```

## Features

- **Multiple Ducks**: Up to `max_ducks` per channel (FIFO targeting of oldest)
- **Despawns**: Ducks despawn after `despawn_time` seconds (configurable)
- **Spawning**: Random spawns every `min_spawn`–`max_spawn` seconds
- **XP System**: Base + bonuses; misses cost XP (-1)
- **Leveling & Stats**: Level-based accuracy, reliability, clip size, magazines
- **Dynamic Ammo**: All HUD lines use level-based clip/mag values; new players start with those capacities
- **Accuracy & Reliability**:
  - Accuracy from the level table (+25% of remaining with Explosive ammo; +10% befriending with Bread)
  - Reliability (jam chance = 1 - reliability); jams require `!reload`; Grease halves jam odds (24h)
- **Golden Ducks**: 5 HP; worth 50 XP; AP/Explosive ammo do 2 dmg vs golden
- **Consumables** (non-stacking): AP, Explosive, Bread, etc.; remaining counts shown in `!duckstats`
- **Infrared Detector**: Trigger lock when no duck (limited uses); from shop (6 uses/24h) or loot (6 uses/24h)
- **Ducks Detector**: 60s pre-spawn notice via NOTICE (24h)
- **Weighted Loot**: 10% on kills only; historically weighted table; most effects last 24h
- **Messaging**: All player responses prefixed with `PLAYERNAME -`
- **Admin/Owner**: Spawn ducks, rearm/disarm, clear channel, etc.
- **Last Duck Tracking**: `!lastduck` shows your last kill time
- **Auto-Restart**: Wrapper script; reconnect logic; MOTD handling
- **No Dependencies**: Pure Python

## Game Mechanics

- **Spawn**: Random spawns per channel up to `max_ducks`; oldest duck is always targeted
- **Shoot or Befriend**: `!bang` applies accuracy/reliability; `!bef` uses befriending accuracy; misses are -1 XP
- **Loot on Kill (10%)**: Weighted random loot; common/uncommon/rare/junk; durations mostly 24h
- **Detectors**:
  - Ducks detector: 60s pre-spawn notice while active (24h)
  - Infrared detector: `!bang` with no duck is safely locked; shop/loot have limited uses
- **Golden**: 5 HP; AP/Explosive do 2 dmg vs golden; Bread improves befriending vs golden
- **Consumables**: Do not stack; must be used up before buying again; shown in `!duckstats`
- **Despawn**: Ducks disappear after `despawn_time`

## Configuration

The bot uses `duckhunt.conf` for all settings:
- IRC server and connection details
- Channel and nickname configuration
- Game timing and XP settings
- Multiple duck limits and despawn times
- Admin user lists
- Perform commands
- Shop item prices

## License

GPLv2 (GNU General Public License v2.0)

This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License version 2 as published by the Free Software Foundation.
