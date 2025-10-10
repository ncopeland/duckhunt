# Duck Hunt IRC Bot v1.0_build78

An advanced IRC bot that hosts Duck Hunt games in IRC channels with full shop system, karma tracking, multi-network support, and multilanguage capabilities. Players shoot ducks with `!bang` when they appear!

## Changelog

### v1.0_build78
- **Bug Fix**: Fixed loot message displaying variable name
  - Changed "you find an extra ammo magazine_capacity!" to "you find an extra magazine!"
  - Affects the loot drop when finding magazines in bushes after killing a duck
  - Much clearer and less confusing

### v1.0_build77
- **Enhancement**: Added personalized quit message on restart
  - Bot now shows "{user} requested restart." when quitting
  - QUIT message sent to all connected networks before exiting
  - Makes it clear who triggered the restart
- **Update**: Updated IRC realname field to show v1.0_build77
  - Bot now properly advertises current version when connecting to IRC
  - Version visible in WHOIS and connection messages

### v1.0_build76
- **Enhancement**: Improved promotion/demotion magazine/ammo mechanics
  - When promoted at max magazines (e.g., 2/2), you now get the new max (e.g., 3/3)
  - Same applies to ammo: if at max ammo, you get the new capacity
  - Added feedback messages: "You found a magazine", "You lost a magazine", etc.
  - Demotion properly caps magazines/ammo with loss messages
  - Creates a more rewarding promotion experience

### v1.0_build75
- **Bug Fix**: Fixed demotion magazine/ammo cap issue
  - When demoted, magazines and ammo now immediately cap to new level limits
  - Prevents having 3/2 magazines (over the max) after demotion
  - Caps are calculated including any upgrade levels the player has purchased
  - Ensures consistent weapon capacity across level changes

### v1.0_build74
- **UI Improvement**: Friendlier message for new players using !duckstats
  - New players now see "You haven't shot any ducks yet! Wait for a duck to spawn and try !bang"
  - Prevents confusing "Error retrieving stats" or "No stats found" messages
  - Different message when checking other players: "{player} hasn't shot any ducks yet in {channel}"
  - Applies to both SQL and JSON backends

### v1.0_build73
- **Critical Fix**: Fixed !duckstats crash for new SQL-backend players
  - Fixed "unsupported format string passed to NoneType" error when displaying stats
  - `best_time` and `total_reaction_time` now properly handle NULL values from database
  - New players created directly in SQL backend now have stats displayed correctly
  - Applies to both stats display and reaction time calculations
- **Critical Fix**: Fixed magazine_capacity initialization for SQL-backend players
  - New players now properly start with magazine_capacity=6 and magazines_max=2
  - Fixed incorrect "Ammo: 6/0" display (was backwards due to 0 magazine_capacity)
  - Migration script included to fix existing affected players (49 records corrected)
  - Ammo mechanics now work correctly for all SQL-backend players

### v1.0_build72
- **UI Improvement**: Cleaned up user validation error messages
  - Removed available users list from error messages for cleaner display
  - Error messages now simply state "User 'X' is not in #channel"
  - Applies to !duckstats, !egg, and shop commands (14, 15, 16, 17)

### v1.0_build71
- **New Feature**: Added owner channel management commands
  - !op <channel> <user> - Owner can op channel members
  - !deop <channel> <user> - Owner can deop channel members
  - Commands work on the network where they're received
  - Includes logging and confirmation messages

### v1.0_build70
- **Bug Fix**: Added user existence validation for targeted commands
  - !duckstats now checks if target user exists in channel before showing stats
  - !egg command validates target user exists before attempting to egg them
  - Shop commands (14, 15, 16, 17) now verify target users exist in channel
  - Helpful error messages show available users when target doesn't exist
  - Prevents generic error messages and wasted XP from invalid targets

### v1.0_build69
- **Bug Fix**: Fixed water bucket (shop item 16) duplicate soaking prevention
  - Now checks if target is already soaked before applying effect
  - Refunds XP if target is already soaked (prevents waste)
  - Maintains proper soaked duration stacking behavior

### v1.0_build68
- **New Feature**: Duck resistance mechanics for !bef command
  - Ducks now have 1/20 chance to hiss ferociously on !bef miss
  - Hissed ducks will also thrash any player attempting !bef with -250 XP penalty
  - Thrashing ducks fly away after attacking (prevents further interaction)
  - Added proper level demotion messages for all XP loss scenarios
- **New Feature**: !egg command for veteran players
  - Unlocked after befriending 50 ducks (hidden "easter egg" feature)
  - 24-hour cooldown per player, throws duck egg at target
  - Egged state requires !shop 12 (spare clothes) to remove
  - Egged players can still use !bef but not !bang (prevents gameplay lockout)
  - Added egged status persistence to database schema
- **New Feature**: Enhanced !duckstats display with red status indicators
  - Removed jammed/confiscated from main stats line for cleaner display
  - Added red [Jammed], [Confiscated], and [Egged] indicators at end when active
  - Status indicators only show when conditions are true (no false positives)
  - Improved message length handling to prevent IRC crashes
- **UI Improvement**: Streamlined weapon stats display
  - Cleaner format: shows only ammo and magazines in [Weapon] section
  - Status conditions now displayed as separate red indicators
  - Better visual separation between different stat categories
- **Naming Update**: Renamed "Trigger Lock" to "Safety Lock" throughout
  - Updated shop menu display and purchase messages
  - Changed all references to use "Safety Lock" terminology
  - Maintains consistency with IRC server filtering requirements

### v1.0_build67
- **Bug Fix**: Fixed shop items that affect other players not saving to database
  - Fixed water bucket (item 16): `soaked_until` now saves to database
  - Fixed sabotage (item 17): `jammed` status now saves to database  
  - Fixed mirror (item 14): `mirror_until` now saves to database
  - Fixed sand (item 15): `sand_until` now saves to database
  - Target player effects now persist correctly across bot restarts
  - All shop items that modify other players now work properly

### v1.0_build66
- **Naming Fix**: Completed renaming "Infrared detector" to "Trigger Lock"
  - Fixed shop menu display: now shows "8- Trigger Lock (15 xp)"
  - Fixed purchase message: now says "Trigger Lock enabled for 24h00m"
  - Fixed duplicate purchase message: now says "Trigger Lock already active"
  - Fixed loot drop messages: now says "find a Trigger Lock"
  - All references now consistently use "Trigger Lock" terminology

### v1.0_build65
- **Critical Fix**: Fixed duck kill counter not incrementing in database
  - Root cause: SQL datetime error was preventing database updates from succeeding
  - Fixed `last_duck_time` field to use proper datetime format instead of Unix timestamp
  - Duck kill counter now properly increments: 8 → 9 → 10 ducks, etc.
  - Database persistence now works correctly for all stat changes
  - Removed debug logging after successful fix

### v1.0_build64
- **Bug Fix**: Fixed `!lastduck` command showing incorrect data
  - `!lastduck` was using in-memory `channel_last_duck_time` dictionary instead of database
  - Now properly reads `last_duck_time` and `ducks_shot` from database
  - Duck kill count and timing now consistent between `!bang` and `!lastduck` commands
  - Fixes issue where `!lastduck` showed "No ducks killed" despite kills being recorded

### v1.0_build63
- **Database Schema Fix**: Added missing shop item columns
  - Added `clover_until`, `clover_bonus` for four-leaf clover (item #10)
  - Added `brush_until` for gun brush (item #13)
  - Added `sight_next_shot` for sight attachment (item #7)
  - Note: Trigger Lock (item #8) uses `trigger_lock_until`, `trigger_lock_uses` (already existed)
  - All 23 shop items now have complete database support
  - Shop item purchases now persist correctly in SQL backend
  - Migration script provided in `migrations/add_shop_items_columns.sql`
  - Schema audit document created: `SCHEMA_AUDIT.md`

### v1.0_build62
- **Critical Fix**: Fixed ammo persistence when hitting golden ducks
  - Golden duck reveal was returning without saving ammo consumption
  - All shots (hit, miss, golden duck) now properly save ammo decrements

### v1.0_build61
- **Critical Fix**: Fixed magazine/ammo persistence for SQL backend
  - `get_channel_stats()` now loads fresh from database for SQL backend
  - Removed hybrid in-memory/SQL cache that caused stale data
  - Magazine decrements from `!reload` now persist correctly
  - All stat modifications now save and load properly

### v1.0_build60
- **Bug Fix**: Fixed Undernet MOTD detection
  - Added handling for IRC 422 (MOTD File is missing) response
  - Undernet now connects immediately instead of waiting 180 seconds for timeout
  - Changed Undernet server to chicago.il.us.undernet.org for better latency

### v1.0_build59
- **Bug Fix**: Fixed misses not saving ammo consumption
  - Moved save logic outside of ricochet victim check
  - All misses now properly save ammo decrements and XP penalties
  - Stats persist correctly after every shot (hit or miss)

### v1.0_build58
- **Critical Bug Fix #3**: Fixed stats not saving to SQL database at all
  - Corrected `_filter_computed_stats()` to only filter penalty/reliability fields
  - `magazine_capacity` and `magazines_max` are persistent upgrade fields and now save correctly
  - All stat changes (ammo, magazines, XP, etc.) now properly persist to database
  - Database timestamps now update correctly after each action

### v1.0_build57
- **Bug Fix Attempt**: Created filtering system for computed stats (had incorrect field list)

### v1.0_build56
- **Critical Bug Fix**: Fixed magazine/ammo stats not saving to SQL database
  - All `!bang`, `!reload`, `!bef`, `!shop`, and admin commands now properly persist state changes to database
  - Magazine count in `!duckstats` now correctly reflects actual remaining magazines
  - Ammo consumption and reload actions are now properly saved
  - Replaced all `save_player_data()` calls with explicit SQL `update_channel_stats()` when using SQL backend

### v1.0_build55
- **Multilanguage Foundation**: Added complete multilanguage support system
  - Created LanguageManager class with IRC color preservation
  - Added 25 language files (English complete, 24 stubs ready for translation)
  - Implemented `!ducklang` command for users to change language preference
  - Color markers (`{{red:text}}`, `{{bold:text}}`) preserve IRC formatting in translations
  - User language preferences saved to `language_prefs.json`
  - Supported languages: English, Spanish, French, German, Russian, Japanese, Mandarin Chinese, Hindi, Arabic, Portuguese, Bengali, Urdu, Indonesian, Nigerian Pidgin, Marathi, Egyptian Arabic, Telugu, Turkish, Tamil, Cantonese, Vietnamese, Wu Chinese, Tagalog, Korean, and Farsi
- **Duck Detector Improvements**: Fixed duplicate purchase bug and added immediate notice when purchased with spawn imminent
- **Documentation**: Added `MULTILANG_ROADMAP.md` with implementation plan for full bot message refactoring
- System ready for incremental translation of bot messages (Phase 1 pending)

### v1.0_build54
- **Rate Limiting**: Added 1 message per second rate limiting per network to prevent flood issues
- **Code Cleanup**: Removed temporary migration and debug scripts from repository
- **Bug Fixes**: Fixed various SQL backend issues with Decimal/float conversions
- Removed duckhunt.data.backup from repo

### v1.0_build53
- Implement lossless backup/restore system for clear command
- Fix clear command for SQL backend and improve network connectivity
- Add MariaDB/MySQL SQL backend support
- Add missing handler methods for commands

### v1.0_build52
- Fix SSL connections for networks requiring secure connections
- Add IPv6 support for servers with IPv6-only interfaces
- Fix magazine capacity upgrade logic (no longer magically adds ammo)
- Replace all "clip" terminology with proper "magazine" terminology
- Fix explosive ammo to decrement on all shots, not just golden ducks
- Rename "infrared detector" to "trigger lock" throughout codebase
- Fix trigger lock purchase confirmation and message visibility
- Fix clear command counting bug and recover lost player data
- Fix data migration to handle legacy field names
- Fix duplicate channel name conflicts across networks with network-prefixed keys
- Fix duck counting logic - regular and golden ducks each count as one
- Add `!topduck duck` command to sort by ducks killed instead of XP
- Enhance `!duckstats` with network/channel display, XP breakdown, and items section

### v1.0_build51
- Fix golden duck survival message colorization
- Fix duck kill message spacing (remove extra space after channel name)

### v1.0_build50
- Fix promotion/demotion message spacing and colorization
- Fix "you missed" message spacing and red colorization
- Fix "empty magazine" message - colorize *CLICK* red
- Fix "no magazines left" message content
- Fix "you reload" message - colorize *CLACK CLACK* red
- Fix "gun doesn't need reload" message - remove grey colorization
- Ensure shop XP penalties are consistently red
- Fix sunglasses purchase logic to prevent duplicate purchases
- Add life remaining display to golden duck hit messages
- Change `!bang` to show remaining duck health instead of damage dealt
- Remove green colorization from shop purchase messages (AP ammo, grease, sight)
- Improve trigger locked message formatting and colorization

### v1.0_build49-48
- Add `!part` command for bot owner to leave channels with proper cleanup
- Fix befriend command message formatting and crashes
- Remove white colorization from various messages
- Add debug logging to duck detector notification system

### Earlier Builds (v1.0_build47 and below)
- Fix duck despawn functionality to properly clean up after 700 seconds
- Fix spawn scheduling to only trigger on appropriate events
- Add MOTD handling for proper bot registration
- Multi-network support with network-specific configurations
- Full shop system with 22+ items
- Karma and XP tracking system
- Level progression with bonuses
- Golden duck mechanics with multi-hit system
- Magazine and ammunition management
- Various items: detector, trigger lock, silencer, insurance, etc.

## Data Storage Options

The bot supports two data storage backends:

### JSON Backend (Default)
- Stores player data in `duckhunt.data` file
- Simple setup, no additional dependencies
- Good for small to medium deployments

### SQL Backend (MariaDB/MySQL)
- Stores player data in MariaDB/MySQL database
- Better performance and scalability
- Supports concurrent access
- Requires `mysql-connector-python` package

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

## SQL Backend Setup

### Prerequisites
1. Install MariaDB/MySQL server
2. Install Python MySQL connector:
   ```bash
   pip3 install mysql-connector-python --break-system-packages
   ```

### Database Setup
1. Run the database setup script:
   ```bash
   python3 setup_database.py
   ```
2. Enter your MySQL root password when prompted
3. The script will create the `duckhunt` database and user

### Data Migration
1. If you have existing JSON data, migrate it to SQL:
   ```bash
   python3 migrate_data.py
   ```
2. Edit `duckhunt.conf` and change `data_storage = sql`

### Configuration
Add these settings to `duckhunt.conf`:
```ini
[DEFAULT]
data_storage = sql
sql_host = localhost
sql_port = 3306
sql_database = duckhunt
sql_user = duckhunt
sql_password = duckhunt123
```

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
