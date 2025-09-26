# Duck Hunt IRC Bot v1.0_build3

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
- `!reload` - Reload your gun
- `!shop` - View purchasable items
- `!duckstats` - View your statistics
- `!topduck` - View leaderboard
- `!duckhelp` - Show help
- `!spawnduck` - Admin: Spawn a duck
- `!spawngold` - Admin: Spawn a golden duck

## Running the Bot

1. First run creates `duckhunt.conf` with default settings
2. Edit `duckhunt.conf` with your IRC server details:
   ```
   server = irc.rizon.net/6667
   ssl = off
   bot_nick = DuckHuntBot,DuckHuntBot2
   channel = #yourchannel
   perform = PRIVMSG YourNick :I am here
   owner = YourNick
   admin = admin1,admin2
   min_spawn = 60
   max_spawn = 180
   gold_ratio = 0.1
   default_xp = 10
   ```

3. Run the bot:
   ```bash
   python3 duckhunt_bot.py
   ```

## Features

- **Duck Spawning**: Random spawns every 1-3 minutes (configurable)
- **XP System**: Earn XP for shooting ducks (configurable default: 10 XP)
- **Leveling**: Gain levels and titles as you progress
- **Shop System**: Buy items with XP (bullets, magazines, ammo types, etc.)
- **Golden Ducks**: Rare golden ducks worth 55 XP
- **Admin Commands**: Spawn ducks, manage the game
- **User Authentication**: WHOIS-based authentication for admin commands
- **Item System**: 23 different purchasable items
- **Bush Searching**: 10% chance to find items after shooting ducks
- **IRC Protocol**: Full IRC implementation with PING/PONG, registration, etc.
- **No Dependencies**: Pure Python, no external libraries required

## Game Mechanics

- **Duck Spawn**: Ducks appear randomly in channels
- **Shooting**: Players have a limited time to shoot ducks with `!bang`
- **XP & Levels**: Gain XP for successful shots, level up for titles
- **Items**: Purchase items from the shop to enhance gameplay
- **Golden Ducks**: Rare spawns worth more XP
- **Bush Search**: Random chance to find items after kills

## Configuration

The bot uses `duckhunt.conf` for all settings:
- IRC server and connection details
- Channel and nickname configuration
- Game timing and XP settings
- Admin user lists
- Perform commands

## License

MIT
