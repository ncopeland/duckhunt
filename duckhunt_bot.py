#!/usr/bin/env python3
"""
Duck Hunt IRC Bot
A simple IRC bot that hosts Duck Hunt games in IRC channels.
"""

import socket
import threading
import time
import re
import random

class DuckHuntBot:
    def __init__(self, server, port, channel, nickname, realname):
        self.server = server
        self.port = port
        self.channel = channel
        self.nickname = nickname
        self.realname = realname
        self.sock = None
        self.game_active = False
        self.duck_position = 0
        self.score = {}
        
    def connect(self):
        """Connect to IRC server"""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.server, self.port))
        
        # Send IRC handshake
        self.send(f"USER {self.nickname} 0 * :{self.realname}")
        self.send(f"NICK {self.nickname}")
        self.send(f"JOIN {self.channel}")
        
    def send(self, message):
        """Send message to IRC server"""
        self.sock.send(f"{message}\r\n".encode('utf-8'))
        
    def send_message(self, message):
        """Send message to channel"""
        self.send(f"PRIVMSG {self.channel} :{message}")
        
    def start_game(self):
        """Start a new Duck Hunt game"""
        self.game_active = True
        self.duck_position = random.randint(1, 10)
        self.send_message("🦆 DUCK HUNT STARTED! A duck is flying across the screen...")
        self.send_message("Type 'shoot <number>' to shoot at position 1-10!")
        self.send_message("The duck is at position " + "?" * 10)
        
    def shoot(self, player, position):
        """Handle shooting attempt"""
        if not self.game_active:
            return
            
        if position == self.duck_position:
            self.send_message(f"🎯 {player} HIT! Duck down at position {position}!")
            if player not in self.score:
                self.score[player] = 0
            self.score[player] += 1
            self.game_active = False
            self.send_message(f"Score: {dict(self.score)}")
            self.send_message("Type '!duckhunt' to start a new game!")
        else:
            self.send_message(f"💨 {player} missed! Duck was at position {self.duck_position}")
            self.game_active = False
            self.send_message("Type '!duckhunt' to try again!")
            
    def run(self):
        """Main bot loop"""
        self.connect()
        
        while True:
            try:
                data = self.sock.recv(1024).decode('utf-8')
                if not data:
                    break
                    
                print(f"Received: {data}")
                
                # Handle PING
                if data.startswith("PING"):
                    self.send(data.replace("PING", "PONG"))
                    
                # Handle channel messages
                if "PRIVMSG" in data and self.channel in data:
                    # Extract sender and message
                    match = re.search(r':([^!]+)![^@]+@[^ ]+ PRIVMSG [^:]+:(.+)', data)
                    if match:
                        sender = match.group(1)
                        message = match.group(2).strip()
                        
                        # Handle commands
                        if message.lower() == "!duckhunt":
                            self.start_game()
                        elif message.lower().startswith("shoot "):
                            try:
                                position = int(message.split()[1])
                                if 1 <= position <= 10:
                                    self.shoot(sender, position)
                                else:
                                    self.send_message(f"{sender}: Position must be between 1-10")
                            except (ValueError, IndexError):
                                self.send_message(f"{sender}: Usage: shoot <1-10>")
                        elif message.lower() == "!score":
                            if self.score:
                                self.send_message(f"Current scores: {dict(self.score)}")
                            else:
                                self.send_message("No scores yet! Play a game with !duckhunt")
                                
            except Exception as e:
                print(f"Error: {e}")
                break
                
        self.sock.close()

if __name__ == "__main__":
    # Configuration - update these for your IRC server
    SERVER = "irc.libera.chat"
    PORT = 6667
    CHANNEL = "#duckhunt"
    NICKNAME = "DuckHuntBot"
    REALNAME = "Duck Hunt Game Bot"
    
    bot = DuckHuntBot(SERVER, PORT, CHANNEL, NICKNAME, REALNAME)
    bot.run()
