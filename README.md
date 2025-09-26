# Duck Hunt IRC Bot

An IRC bot that hosts Duck Hunt games in IRC channels. Players can shoot ducks by guessing their position!

## How to Play

1. Join the IRC channel where the bot is running
2. Type `!duckhunt` to start a new game
3. A duck will fly across 10 positions (1-10)
4. Type `shoot <number>` to shoot at that position
5. Hit the duck to score points!
6. Type `!score` to see current scores

## Running the Bot

1. Edit the configuration in `duckhunt_bot.py`:
   - `SERVER`: IRC server (default: irc.libera.chat)
   - `PORT`: IRC port (default: 6667)
   - `CHANNEL`: Channel to join (default: #duckhunt)
   - `NICKNAME`: Bot nickname

2. Run the bot:
   ```bash
   python3 duckhunt_bot.py
   ```

## Features

- Simple IRC protocol implementation
- Duck Hunt game mechanics
- Score tracking
- No external dependencies (pure Python)

## License

MIT
