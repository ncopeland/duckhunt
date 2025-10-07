#!/bin/bash
cd /home/boliver/Projects/duckhunt
pkill -f duckhunt_bot.py
sleep 2
nohup python3 duckhunt_bot.py > bot.out 2>&1 &
echo "Bot started. Check bot.out for output."
sleep 2
tail -20 bot.out




