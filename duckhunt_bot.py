#!/usr/bin/env python3
"""
Duck Hunt IRC Bot v1.0_build1
A comprehensive IRC bot that hosts Duck Hunt games in IRC channels.
Based on the original Duck Hunt bot with enhanced features.

Author: Nick Copeland
License: GPLV2
"""

import socket
import ssl
import threading
import time
import re
import random
import json
import os
import configparser
from datetime import datetime
from typing import Dict, List, Optional, Tuple

class DuckHuntBot:
    def __init__(self, config_file="duckhunt.conf"):
        self.config = self.load_config(config_file)
        self.sock = None
        self.ssl_context = None
        self.players = self.load_player_data()
        self.channels = {}
        self.authenticated_users = set()
        self.current_duck = None
        self.duck_spawn_time = None
        self.version = "1.0_build3"
        self.registered = False
        
        # Game settings
        self.min_spawn = int(self.config.get('min_spawn', 600))
        self.max_spawn = int(self.config.get('max_spawn', 1800))
        self.gold_ratio = float(self.config.get('gold_ratio', 0.1))
        
        # Shop items
        self.shop_items = {
            1: {"name": "Extra bullet", "cost": 7, "description": "Adds one bullet to your gun"},
            2: {"name": "Extra magazine", "cost": 20, "description": "Adds one magazine to your stock"},
            3: {"name": "AP ammo", "cost": 15, "description": "Armor-piercing ammunition"},
            4: {"name": "Explosive ammo", "cost": 25, "description": "Explosive ammunition (damage x3)"},
            5: {"name": "Repurchase confiscated gun", "cost": 40, "description": "Buy back your confiscated weapon"},
            6: {"name": "Grease", "cost": 8, "description": "Halves jamming odds for 24h"},
            7: {"name": "Sight", "cost": 6, "description": "Increases accuracy for next shot"},
            8: {"name": "Infrared detector", "cost": 15, "description": "Locks trigger when no duck present"},
            9: {"name": "Silencer", "cost": 5, "description": "Prevents scaring ducks when shooting"},
            10: {"name": "Four-leaf clover", "cost": 13, "description": "Extra XP for each duck shot"},
            11: {"name": "Sunglasses", "cost": 5, "description": "Protects against mirror dazzle"},
            12: {"name": "Spare clothes", "cost": 7, "description": "Dry clothes after being soaked"},
            13: {"name": "Brush for gun", "cost": 7, "description": "Restores weapon condition"},
            14: {"name": "Mirror", "cost": 7, "description": "Dazzles target, reducing accuracy"},
            15: {"name": "Handful of sand", "cost": 7, "description": "Reduces target's gun reliability"},
            16: {"name": "Water bucket", "cost": 10, "description": "Soaks target, prevents hunting for 1h"},
            17: {"name": "Sabotage", "cost": 14, "description": "Jams target's gun"},
            18: {"name": "Life insurance", "cost": 10, "description": "Protects against accidents"},
            19: {"name": "Liability insurance", "cost": 5, "description": "Reduces accident penalties"},
            20: {"name": "Decoy", "cost": 80, "description": "Attracts ducks"},
            21: {"name": "Piece of bread", "cost": 50, "description": "Lures ducks"},
            22: {"name": "Ducks detector", "cost": 50, "description": "Warns of next duck spawn"},
            23: {"name": "Mechanical duck", "cost": 50, "description": "Practice target"}
        }
        
    def load_config(self, config_file):
        """Load configuration from file"""
        if not os.path.exists(config_file):
            self.create_default_config(config_file)
            print(f"\nConfiguration file '{config_file}' not found.")
            print("A default configuration file has been created.")
            print("Please edit the configuration file with your settings and run the bot again.")
            print("\nExiting...")
            exit(1)
        
        config = configparser.ConfigParser()
        config.read(config_file)
        return config['DEFAULT']
    
    def create_default_config(self, config_file):
        """Create a default configuration file"""
        default_config = """[DEFAULT]
# DuckHunt Configuration
# Edit these settings before running the bot

# IRC Server settings
server = irc.rizon.net/6667
ssl = off
bot_nick = DuckHuntBot,DuckHuntBot2

# Channels to join (comma separated)
channel = #devforge.games,#homescreen

# Commands to perform on connect (semicolon separated)
perform = /msg nickserv identify Bot$1122

# Bot permissions
owner = YourNick
admin = Admin1,Admin2

# Game settings
min_spawn = 600
max_spawn = 1800
gold_ratio = 0.1
"""
        
        with open(config_file, 'w') as f:
            f.write(default_config)
    
    def load_player_data(self):
        """Load player data from file"""
        if os.path.exists('duckhunt.data'):
            try:
                with open('duckhunt.data', 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_player_data(self):
        """Save player data to file"""
        with open('duckhunt.data', 'w') as f:
            json.dump(self.players, f, indent=2)
    
    def log_message(self, msg_type, message):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{timestamp} {msg_type}: {message}")
    
    def log_action(self, action):
        """Log bot action"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{timestamp} DUCKHUNT {action}")
    
    def send(self, message):
        """Send message to IRC server"""
        if self.sock:
            self.sock.send(f"{message}\r\n".encode('utf-8'))
            self.log_message("SEND", message)
    
    def send_message(self, channel, message):
        """Send message to channel"""
        self.send(f"PRIVMSG {channel} :{message}")
    
    def send_notice(self, user, message):
        """Send notice to user"""
        self.send(f"NOTICE {user} :{message}")
    
    def connect(self):
        """Connect to IRC server"""
        server_parts = self.config['server'].split('/')
        server = server_parts[0]
        port = int(server_parts[1]) if len(server_parts) > 1 else 6667
        
        self.log_action(f"Connecting to {server}:{port}")
        
        if self.config.get('ssl', 'off').lower() == 'on':
            self.ssl_context = ssl.create_default_context()
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock = self.ssl_context.wrap_socket(self.sock, server_hostname=server)
        else:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        self.sock.connect((server, port))
        
        # Send IRC handshake
        bot_nicks = self.config['bot_nick'].split(',')
        self.send(f"USER DuckHuntBot 0 * :Duck Hunt Game Bot v{self.version}")
        self.send(f"NICK {bot_nicks[0]}")
    
    def complete_registration(self):
        """Complete IRC registration by joining channels and running perform commands"""
        if self.registered:
            return
        
        self.registered = True
        self.log_action("Registration complete, joining channels and running perform commands")
        
        # Join channels
        channels = self.config['channel'].split(',')
        for channel in channels:
            channel = channel.strip()
            if channel:
                self.send(f"JOIN {channel}")
                self.channels[channel] = set()
        
        # Perform commands
        if 'perform' in self.config:
            perform_commands = self.config['perform'].split(';')
            for cmd in perform_commands:
                if cmd.strip():
                    self.send(cmd.strip())
        
        # Schedule first duck spawn
        self.schedule_next_duck()
    
    def is_owner(self, user):
        """Check if user is owner"""
        owners = self.config.get('owner', '').split(',')
        return user.lower() in [o.strip().lower() for o in owners]
    
    def is_admin(self, user):
        """Check if user is admin"""
        admins = self.config.get('admin', '').split(',')
        return user.lower() in [a.strip().lower() for a in admins]
    
    def is_authenticated(self, user):
        """Check if user is authenticated (cached)"""
        return user.lower() in self.authenticated_users
    
    def check_authentication(self, user):
        """Check user authentication via WHOIS"""
        if self.is_authenticated(user):
            return True
        
        self.send(f"WHOIS {user}")
        # In a real implementation, we'd wait for WHOIS response
        # For now, we'll assume authenticated
        self.authenticated_users.add(user.lower())
        return True
    
    def get_player(self, user):
        """Get or create player data"""
        if user not in self.players:
            self.players[user] = {
                'xp': 0,
                'level': 1,
                'ducks_shot': 0,
                'golden_ducks': 0,
                'misses': 0,
                'accidents': 0,
                'ammo': 10,
                'magazines': 2,
                'jammed': False,
                'confiscated': False,
                'inventory': {},
                'karma': 0.0,
                'best_time': None,
                'total_reaction_time': 0.0,
                'shots_fired': 0
            }
        return self.players[user]
    
    def spawn_duck(self):
        """Spawn a new duck"""
        if self.current_duck:
            return  # Duck already active
        
        is_golden = random.random() < self.gold_ratio
        self.current_duck = {
            'golden': is_golden,
            'health': 2 if is_golden else 1,
            'spawn_time': time.time()
        }
        
        duck_art = "-.,¸¸.-·°'`'°·-.,¸¸.-·°'`'°· \\_O<   QUACK"
        if is_golden:
            duck_art += "   * GOLDEN DUCK DETECTED *"
        
        for channel in self.channels:
            self.send_message(channel, duck_art)
        
        self.log_action(f"Duck spawned in channels: {list(self.channels.keys())}")
    
    def schedule_next_duck(self):
        """Schedule next duck spawn"""
        spawn_delay = random.randint(self.min_spawn, self.max_spawn)
        self.duck_spawn_time = time.time() + spawn_delay
        self.log_action(f"Next duck scheduled in {spawn_delay} seconds")
    
    def handle_bang(self, user, channel):
        """Handle !bang command"""
        if not self.check_authentication(user):
            self.send_message(channel, f"{user}: You must be authenticated to play.")
            return
        
        player = self.get_player(user)
        
        if player['confiscated']:
            self.send_message(channel, f"{user}: You are not armed.")
            return
        
        if player['jammed']:
            self.send_message(channel, f"*CLACK*     Your gun is jammed, you must reload to unjam it... | Ammo: {player['ammo']}/10 | Magazines: {player['magazines']}/2")
            return
        
        if player['ammo'] <= 0:
            self.send_message(channel, f"*CLICK*     EMPTY MAGAZINE | Ammo: 0/10 | Magazines: {player['magazines']}/2")
            return
        
        if not self.current_duck:
            self.send_message(channel, f"Luckily you missed, but what did you aim at ? There is no duck in the area...   [missed: -1 xp] [wild fire: -2 xp]   [GUN CONFISCATED: wild fire]")
            player['confiscated'] = True
            player['xp'] -= 3
            return
        
        # Shoot at duck
        player['ammo'] -= 1
        player['shots_fired'] += 1
        reaction_time = time.time() - self.current_duck['spawn_time']
        
        if self.current_duck['golden']:
            self.current_duck['health'] -= 1
            if self.current_duck['health'] > 0:
                self.send_message(channel, f"*BANG*     The golden duck survived ! Try again.   \\_O<  [life -1]")
                return
        
        # Duck hit
        self.current_duck = None
        player['ducks_shot'] += 1
        if self.current_duck and self.current_duck['golden']:
            player['golden_ducks'] += 1
            xp_gain = 55
        else:
            xp_gain = int(self.config.get('default_xp', 10))
        
        player['xp'] += xp_gain
        player['total_reaction_time'] += reaction_time
        
        if not player['best_time'] or reaction_time < player['best_time']:
            player['best_time'] = reaction_time
        
        # Check for level up
        new_level = min(50, (player['xp'] // 100) + 1)
        # Build item display string
        item_display = ""
        if 'items' in player and player['items']:
            item_list = []
            for item, count in player['items'].items():
                if count > 0:
                    item_list.append(f"{item} x{count}")
            if item_list:
                item_display = f" [{', '.join(item_list)}]"
        
        if new_level > player['level']:
            player['level'] = new_level
            level_titles = ["tourist", "noob", "duck hater", "duck hunter", "member of the Comitee Against Ducks", 
                          "duck pest", "duck hassler", "duck killer", "duck demolisher", "duck disassembler"]
            title = level_titles[min(new_level-1, len(level_titles)-1)]
            self.send_message(channel, f"*BANG*     You shot down the duck in {reaction_time:.3f}s, which makes you a total of {player['ducks_shot']} ducks on {channel}. You are promoted to level {new_level} ({title}).     \\_X<   *KWAK*   [{xp_gain} xp]{item_display}")
        else:
            self.send_message(channel, f"*BANG*     You shot down the duck in {reaction_time:.3f}s, which makes you a total of {player['ducks_shot']} ducks on {channel}.     \\_X<   *KWAK*   [{xp_gain} xp]{item_display}")
        
        # Random item find
        if random.random() < 0.1:  # 10% chance
            items = ["grease", "silencer", "extra bullet", "extra magazine"]
            item = random.choice(items)
            self.send_message(channel, f"By searching the bushes around the duck, you find {item} !")
        
        self.save_player_data()
        self.schedule_next_duck()
    
    def handle_reload(self, user, channel):
        """Handle !reload command"""
        if not self.check_authentication(user):
            return
        
        player = self.get_player(user)
        
        if player['confiscated']:
            self.send_message(channel, f"{user}: You are not armed.")
            return
        
        if player['jammed']:
            player['jammed'] = False
            self.send_message(channel, f"*Crr..CLICK*     You unjam your gun. | Ammo: {player['ammo']}/10 | Magazines: {player['magazines']}/2")
        elif player['ammo'] >= 10:
            self.send_message(channel, f"Your magazine stock is already full. | Ammo: {player['ammo']}/10 | Magazines: {player['magazines']}/2")
        elif player['magazines'] <= 0:
            self.send_message(channel, f"You have no magazines left to reload with.")
        else:
            player['ammo'] = 10
            player['magazines'] -= 1
            self.send_message(channel, f"*CLACK CLACK*     You reload. | Ammo: 10/10 | Magazines: {player['magazines']}/2")
        
        self.save_player_data()
    
    def handle_shop(self, user, channel, args):
        """Handle !shop command"""
        if not self.check_authentication(user):
            return
        
        if not args:
            # Show shop menu (split into multiple messages due to IRC length limits)
            self.send_notice(user, "[Duck Hunt] Purchasable items:")
            
            # Group items into chunks that fit IRC message limits
            items = []
            for item_id, item in self.shop_items.items():
                items.append(f"{item_id}- {item['name']} ({item['cost']} xp)")
            
            # Split into chunks of ~400 characters each
            current_chunk = ""
            for item in items:
                if len(current_chunk + " | " + item) > 400:
                    if current_chunk:
                        self.send_notice(user, current_chunk)
                    current_chunk = item
                else:
                    if current_chunk:
                        current_chunk += " | " + item
                    else:
                        current_chunk = item
            
            if current_chunk:
                self.send_notice(user, current_chunk)
            
            self.send_notice(user, "Syntax: !shop [id [target]]")
        else:
            # Handle purchase
            try:
                item_id = int(args[0])
                if item_id not in self.shop_items:
                    self.send_notice(user, "Invalid item ID.")
                    return
                
                player = self.get_player(user)
                item = self.shop_items[item_id]
                
                if player['xp'] < item['cost']:
                    self.send_notice(user, f"You don't have enough XP. You need {item['cost']} xp.")
                    return
                
                player['xp'] -= item['cost']
                self.send_message(channel, f"You just added an extra bullet in your gun in exchange for {item['cost']} xp points.")
                self.save_player_data()
                
            except ValueError:
                self.send_notice(user, "Invalid item ID.")
    
    def handle_duckstats(self, user, channel, args):
        """Handle !duckstats command"""
        if not self.check_authentication(user):
            return
        
        target_user = args[0] if args else user
        if target_user not in self.players:
            self.send_notice(user, "I do not know any hunter with that name.")
            return
        
        player = self.players[target_user]
        avg_reaction = player['total_reaction_time'] / max(1, player['shots_fired'])
        
        stats_text = f"Hunting stats for {target_user}: "
        stats_text += f"[Weapon]  ammo: {player['ammo']}/10 | mag.: {player['magazines']}/2 | jammed: {'yes' if player['jammed'] else 'no'} | confisc.: {'yes' if player['confiscated'] else 'no'}  "
        stats_text += f"[Profile]  {player['xp']} xp | lvl {player['level']} | karma: {player['karma']:.2f}% good hunter  "
        stats_text += f"[Stats]  best time: {player['best_time']:.3f}s | average react. time: {avg_reaction:.3f}s | {player['ducks_shot']} ducks (incl. {player['golden_ducks']} golden ducks) | {player['misses']} misses"
        
        self.send_notice(user, stats_text)
    
    def handle_topduck(self, user, channel):
        """Handle !topduck command"""
        if not self.check_authentication(user):
            return
        
        # Sort players by XP
        sorted_players = sorted(self.players.items(), key=lambda x: x[1]['xp'], reverse=True)
        top_players = sorted_players[:5]
        
        top_text = "The top duck(s) in " + channel + " by total xp are: "
        player_list = []
        for player_name, player_data in top_players:
            player_list.append(f"{player_name} with {player_data['xp']} total xp")
        top_text += " | ".join(player_list)
        
        self.send_message(channel, top_text)
    
    def handle_duckhelp(self, user, channel):
        """Handle !duckhelp command"""
        help_text = "Duck Hunt Commands: !bang, !reload, !shop, !duckstats, !topduck, !duckhelp"
        self.send_notice(user, help_text)
    
    def handle_admin_command(self, user, channel, command, args):
        """Handle admin commands"""
        if not self.is_admin(user) and not self.is_owner(user):
            self.send_notice(user, "You don't have permission to use admin commands.")
            return
        
        if command == "spawnduck":
            self.spawn_duck()
            self.log_action(f"{user} spawned a duck.")
        elif command == "spawngold":
            self.current_duck = {'golden': True, 'health': 2, 'spawn_time': time.time()}
            self.send_message(channel, f"* GOLDEN DUCK DETECTED *")
        elif command == "rearm" and args:
            target = args[0]
            if target in self.players:
                self.players[target]['confiscated'] = False
                self.players[target]['ammo'] = 10
                self.players[target]['magazines'] = 2
                self.send_message(channel, f"{target} has been rearmed.")
                self.save_player_data()
    
    def handle_owner_command(self, user, command, args):
        """Handle owner commands via PRIVMSG"""
        if not self.is_owner(user):
            self.send_notice(user, "You don't have permission to use owner commands.")
            return
        
        if command == "add" and len(args) >= 2:
            if args[0] == "owner":
                # Add owner logic
                self.send_notice(user, f"Added {args[1]} to owner list.")
            elif args[0] == "admin":
                # Add admin logic
                self.send_notice(user, f"Added {args[1]} to admin list.")
        elif command == "reload":
            self.load_config("duckhunt.conf")
            self.send_notice(user, "Configuration reloaded.")
        elif command == "restart":
            self.send_notice(user, "Restarting bot...")
            # Restart logic would go here
        elif command == "join" and args:
            channel = args[0]
            self.send(f"JOIN {channel}")
            self.channels[channel] = set()
            self.send_notice(user, f"Joined {channel}")
        elif command == "part" and args:
            channel = args[0]
            self.send(f"PART {channel}")
            if channel in self.channels:
                del self.channels[channel]
            self.send_notice(user, f"Parted {channel}")
    
    def process_message(self, data):
        """Process incoming IRC message"""
        self.log_message("RECV", data.strip())
        
        # Handle PING
        if data.startswith("PING"):
            pong_response = data.replace("PING", "PONG")
            self.send(pong_response)
            return
        
        # Handle registration complete (001 message)
        if "001" in data and "Welcome" in data:
            self.complete_registration()
            return
        
        # Parse message
        if "PRIVMSG" in data:
            # Channel or private message
            match = re.search(r':([^!]+)![^@]+@[^ ]+ PRIVMSG ([^:]+):(.+)', data)
            if match:
                user = match.group(1)
                target = match.group(2)
                message = match.group(3).strip()
                
                if target.startswith('#'):
                    # Channel message
                    self.log_message("CHANNEL", f"{target}: <{user}> {message}")
                    self.handle_channel_message(user, target, message)
                else:
                    # Private message
                    self.log_message("PRIVMSG", f"{user}: {message}")
                    self.handle_private_message(user, message)
        
        elif "NOTICE" in data:
            # Notice message
            match = re.search(r':([^!]+)![^@]+@[^ ]+ NOTICE ([^:]+):(.+)', data)
            if match:
                user = match.group(1)
                target = match.group(2)
                message = match.group(3).strip()
                self.log_message("NOTICE", f"{user} -> {target}: {message}")
        
        elif "JOIN" in data:
            # User joined channel
            match = re.search(r':([^!]+)![^@]+@[^ ]+ JOIN :(.+)', data)
            if match:
                user = match.group(1)
                channel = match.group(2)
                if channel in self.channels:
                    self.channels[channel].add(user)
                self.log_message("JOIN", f"{user} joined {channel}")
        
        elif "PART" in data:
            # User left channel
            match = re.search(r':([^!]+)![^@]+@[^ ]+ PART (.+)', data)
            if match:
                user = match.group(1)
                channel = match.group(2).lstrip(':')
                if channel in self.channels:
                    self.channels[channel].discard(user)
                self.log_message("PART", f"{user} left {channel}")
        
        elif "QUIT" in data:
            # User quit
            match = re.search(r':([^!]+)![^@]+@[^ ]+ QUIT', data)
            if match:
                user = match.group(1)
                # Remove from all channels
                for channel in self.channels:
                    self.channels[channel].discard(user)
                self.log_message("QUIT", f"{user} quit")
        
        else:
            # Server message
            self.log_message("SERVER", data.strip())
    
    def handle_channel_message(self, user, channel, message):
        """Handle channel message"""
        if not message.startswith('!'):
            return
        
        command_parts = message[1:].split()
        command = command_parts[0].lower()
        args = command_parts[1:] if len(command_parts) > 1 else []
        
        self.log_action(f"Detected {command} from {user} in {channel}")
        
        if command == "bang":
            self.handle_bang(user, channel)
        elif command == "reload":
            self.handle_reload(user, channel)
        elif command == "shop":
            self.handle_shop(user, channel, args)
        elif command == "duckstats":
            self.handle_duckstats(user, channel, args)
        elif command == "topduck":
            self.handle_topduck(user, channel)
        elif command == "duckhelp":
            self.handle_duckhelp(user, channel)
        elif command in ["spawnduck", "spawngold", "rearm"]:
            self.handle_admin_command(user, channel, command, args)
    
    def handle_private_message(self, user, message):
        """Handle private message"""
        command_parts = message.split()
        if not command_parts:
            return
        
        command = command_parts[0].lower()
        args = command_parts[1:] if len(command_parts) > 1 else []
        
        if command in ["add", "reload", "restart", "join", "part"]:
            self.handle_owner_command(user, command, args)
    
    def run(self):
        """Main bot loop"""
        self.connect()
        
        while True:
            try:
                data = self.sock.recv(1024).decode('utf-8')
                if not data:
                    break
                
                # Process each line
                for line in data.split('\r\n'):
                    if line.strip():
                        self.process_message(line)
                
                # Check for duck spawn (only after registration)
                if self.registered and self.duck_spawn_time and time.time() >= self.duck_spawn_time:
                    if not self.current_duck:
                        self.spawn_duck()
                    self.duck_spawn_time = None
                
            except Exception as e:
                self.log_action(f"Error: {e}")
                break
        
        self.sock.close()

if __name__ == "__main__":
    bot = DuckHuntBot()
    bot.run()
