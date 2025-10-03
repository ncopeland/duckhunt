#!/usr/bin/env python3
"""
Duck Hunt IRC Bot v1.0
A comprehensive IRC bot that hosts Duck Hunt games in IRC channels.
Based on the original Duck Hunt bot with enhanced features.

Author: Nick Copeland
License: GPLV2
"""

import asyncio
import socket
import ssl
import math
import time
import re
import random
import json
import os
import configparser
from datetime import datetime
from typing import Dict, List, Optional, Tuple

class NetworkConnection:
    """Represents a connection to a single IRC network"""
    def __init__(self, name: str, config: dict):
        self.name = name
        self.config = config
        self.sock = None
        self.ssl_context = None
        self.registered = False
        self.motd_timeout_triggered = False
        self.message_count = 0
        self.motd_message_count = 0
        self.nick = config['bot_nick'].split(',')[0]
        self.channels = {}  # {channel: set(users)}
        self.channel_next_spawn = {}
        self.channel_pre_notice = {}
        self.channel_notice_sent = {}
        self.channel_last_spawn = {}
        self.last_despawn_check = 0

class DuckHuntBot:
    def __init__(self, config_file="duckhunt.conf"):
        self.config = self.load_config(config_file)
        self.players = self.load_player_data()
        self.authenticated_users = set()
        self.channel_ducks = {}  # Per-channel duck lists: {channel: [{'spawn_time': time, 'golden': bool}]}
        self.active_ducks = {}  # Per-channel duck lists: {channel: [ {'spawn_time': time, 'golden': bool, 'health': int}, ... ]}
        self.channel_last_duck_time = {}  # {channel: timestamp} - tracks when last duck was killed in each channel
        # Legacy global fields retained for backward compatibility (unused by per-channel scheduler)
        self.duck_spawn_time = None
        self.version = "1.0_build39"
        self.ducks_lock = asyncio.Lock()
        # Next spawn pre-notice tracking
        self.next_spawn_channel = None
        self.pre_spawn_notice_time = None
        self.next_spawn_notice_sent = False
        
        # Multi-network support
        self.networks = {}  # {network_name: NetworkConnection}
        self.setup_networks()
    
    def setup_networks(self):
        """Setup network connections from config"""
        # Look for network sections in config
        network_sections = [section for section in self.config.sections() if section.startswith('network:')]
        
        if network_sections:
            # Multi-network configuration
            for section in network_sections:
                network_name = section.split(':', 1)[1]  # Extract name after 'network:'
                network_config = dict(self.config[section])
                self.networks[network_name] = NetworkConnection(network_name, network_config)
        else:
            # Fallback to single network from DEFAULT section
            main_config = {
                'server': self.config.get('DEFAULT', 'server', fallback='irc.rizon.net/6667'),
                'ssl': self.config.get('DEFAULT', 'ssl', fallback='off'),
                'bot_nick': self.config.get('DEFAULT', 'bot_nick', fallback='DuckHuntBot'),
                'channel': self.config.get('DEFAULT', 'channel', fallback='#default'),
                'perform': self.config.get('DEFAULT', 'perform', fallback=''),
                'owner': self.config.get('DEFAULT', 'owner', fallback=''),
                'admin': self.config.get('DEFAULT', 'admin', fallback=''),
            }
            self.networks['main'] = NetworkConnection('main', main_config)
        
        # Default game settings (fallback for backward compatibility)
        self.min_spawn = int(self.config.get('DEFAULT', 'min_spawn', fallback=600))
        self.max_spawn = int(self.config.get('DEFAULT', 'max_spawn', fallback=1800))
        self.gold_ratio = float(self.config.get('DEFAULT', 'gold_ratio', fallback=0.1))
        self.max_ducks = int(self.config.get('DEFAULT', 'max_ducks', fallback=5))
        self.despawn_time = int(self.config.get('DEFAULT', 'despawn_time', fallback=720))  # 12 minutes default
        
        # Shop items (prices loaded from config)
        self.shop_items = {
            1: {"name": "Extra bullet", "cost": int(self.config.get('DEFAULT', 'shop_extra_bullet', fallback=7)), "description": "Adds one bullet to your gun"},
            2: {"name": "Refill magazine", "cost": int(self.config.get('DEFAULT', 'shop_extra_magazine', fallback=20)), "description": "Adds one spare magazine to your stock"},
            3: {"name": "AP ammo", "cost": int(self.config.get('DEFAULT', 'shop_ap_ammo', fallback=15)), "description": "Armor-piercing ammunition"},
            4: {"name": "Explosive ammo", "cost": int(self.config.get('DEFAULT', 'shop_explosive_ammo', fallback=25)), "description": "Explosive ammunition (damage x3)"},
            5: {"name": "Repurchase confiscated gun", "cost": int(self.config.get('DEFAULT', 'shop_repurchase_gun', fallback=40)), "description": "Buy back your confiscated weapon"},
            6: {"name": "Grease", "cost": int(self.config.get('DEFAULT', 'shop_grease', fallback=8)), "description": "Halves jamming odds for 24h"},
            7: {"name": "Sight", "cost": int(self.config.get('DEFAULT', 'shop_sight', fallback=6)), "description": "Increases accuracy for next shot"},
            8: {"name": "Infrared detector", "cost": int(self.config.get('DEFAULT', 'shop_infrared_detector', fallback=15)), "description": "Locks trigger when no duck present"},
            9: {"name": "Silencer", "cost": int(self.config.get('DEFAULT', 'shop_silencer', fallback=5)), "description": "Prevents scaring ducks when shooting"},
            10: {"name": "Four-leaf clover", "cost": int(self.config.get('DEFAULT', 'shop_four_leaf_clover', fallback=13)), "description": "Extra XP for each duck shot"},
            11: {"name": "Sunglasses", "cost": int(self.config.get('DEFAULT', 'shop_sunglasses', fallback=5)), "description": "Protects against mirror dazzle"},
            12: {"name": "Spare clothes", "cost": int(self.config.get('DEFAULT', 'shop_spare_clothes', fallback=7)), "description": "Dry clothes after being soaked"},
            13: {"name": "Brush for gun", "cost": int(self.config.get('DEFAULT', 'shop_brush_for_gun', fallback=7)), "description": "Restores weapon condition"},
            14: {"name": "Mirror", "cost": int(self.config.get('DEFAULT', 'shop_mirror', fallback=7)), "description": "Dazzles target, reducing accuracy"},
            15: {"name": "Handful of sand", "cost": int(self.config.get('DEFAULT', 'shop_handful_of_sand', fallback=7)), "description": "Reduces target's gun reliability"},
            16: {"name": "Water bucket", "cost": int(self.config.get('DEFAULT', 'shop_water_bucket', fallback=10)), "description": "Soaks target, prevents hunting for 1h"},
            17: {"name": "Sabotage", "cost": int(self.config.get('DEFAULT', 'shop_sabotage', fallback=14)), "description": "Jams target's gun"},
            18: {"name": "Life insurance", "cost": int(self.config.get('DEFAULT', 'shop_life_insurance', fallback=10)), "description": "Protects against accidents"},
            19: {"name": "Liability insurance", "cost": int(self.config.get('DEFAULT', 'shop_liability_insurance', fallback=5)), "description": "Reduces accident penalties"},
            20: {"name": "Piece of bread", "cost": int(self.config.get('DEFAULT', 'shop_piece_of_bread', fallback=50)), "description": "Lures ducks"},
            21: {"name": "Ducks detector", "cost": int(self.config.get('DEFAULT', 'shop_ducks_detector', fallback=50)), "description": "Warns of next duck spawn"},
            22: {"name": "Upgrade Magazine", "cost": 200, "description": "Increase ammo per magazine (up to 5 levels)"},
            23: {"name": "Extra Magazine", "cost": 200, "description": "Increase max carried magazines (up to 5 levels)"}
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
        return config
    
    def create_default_config(self, config_file):
        """Create a default configuration file"""
        default_config = """[DEFAULT]
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
"""
        
        with open(config_file, 'w') as f:
            f.write(default_config)
    
    def load_player_data(self):
        """Load player data from file"""
        if os.path.exists('duckhunt.data'):
            try:
                with open('duckhunt.data', 'r') as f:
                    players = json.load(f)
                    # Ensure all players have required fields and migrate to new structure
                    for player_name, player_data in players.items():
                        if 'sabotaged' not in player_data:
                            player_data['sabotaged'] = False
                        
                        # Migrate old stats to channel_stats structure
                        if 'channel_stats' not in player_data:
                            # Create channel_stats from old global stats
                            player_data['channel_stats'] = {}
                            
                            # Migrate stats to a default channel (we'll use the first channel from config)
                            default_channel = self.config.get('channel', '#default').split(',')[0]
                            
                            # Store old values before deleting
                            old_xp = player_data.get('xp', 0)
                            old_ducks_shot = player_data.get('ducks_shot', 0)
                            old_golden_ducks = player_data.get('golden_ducks', 0)
                            old_misses = player_data.get('misses', 0)
                            old_accidents = player_data.get('accidents', 0)
                            old_best_time = player_data.get('best_time')
                            old_total_reaction_time = player_data.get('total_reaction_time', 0.0)
                            old_shots_fired = player_data.get('shots_fired', 0)
                            old_last_duck_time = player_data.get('last_duck_time')
                            
                            player_data['channel_stats'][default_channel] = {
                                'xp': old_xp,
                                'ducks_shot': old_ducks_shot,
                                'golden_ducks': old_golden_ducks,
                                'misses': old_misses,
                                'accidents': old_accidents,
                                'best_time': old_best_time,
                                'total_reaction_time': old_total_reaction_time,
                                'shots_fired': old_shots_fired,
                                'last_duck_time': old_last_duck_time
                            }
                            
                            # Remove old global stats (including XP and level now)
                            for old_field in ['xp', 'level', 'ducks_shot', 'golden_ducks', 'misses', 'accidents', 'best_time', 'total_reaction_time', 'shots_fired', 'last_duck_time']:
                                if old_field in player_data:
                                    del player_data[old_field]
                        else:
                            # channel_stats exists, but check if it needs XP migration
                            old_xp = player_data.get('xp', 0)
                            old_level = player_data.get('level', 1)
                            
                            # If we have old global XP/level, migrate to first channel
                            if old_xp > 0 or old_level > 1:
                                default_channel = self.config.get('channel', '#default').split(',')[0]
                                if default_channel not in player_data['channel_stats']:
                                    player_data['channel_stats'][default_channel] = {
                                        'xp': 0,
                                        'ducks_shot': 0,
                                        'golden_ducks': 0,
                                        'misses': 0,
                                        'accidents': 0,
                                        'best_time': None,
                                        'total_reaction_time': 0.0,
                                        'shots_fired': 0,
                                        'last_duck_time': None
                                    }
                                
                                # Add old XP to the default channel
                                player_data['channel_stats'][default_channel]['xp'] += old_xp
                            
                            # Remove old global stats
                            for old_field in ['xp', 'level']:
                                if old_field in player_data:
                                    del player_data[old_field]
                            
                            # Ensure all existing channel_stats have required fields
                            for channel, stats in player_data['channel_stats'].items():
                                if 'xp' not in stats:
                                    stats['xp'] = 0
                                if 'confiscated' not in stats:
                                    stats['confiscated'] = False
                                if 'jammed' not in stats:
                                    stats['jammed'] = False
                                if 'sabotaged' not in stats:
                                    stats['sabotaged'] = False
                                if 'ammo' not in stats:
                                    stats['ammo'] = 10
                                if 'magazines' not in stats:
                                    stats['magazines'] = 2
                                if 'befriended_ducks' not in stats:
                                    stats['befriended_ducks'] = 0
                    
                    return players
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
        log_entry = f"{timestamp} {msg_type}: {message}\n"
        self._write_to_log_file(log_entry)
    
    def log_action(self, action):
        """Log bot action"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"{timestamp} DUCKHUNT {action}\n"
        self._write_to_log_file(log_entry)
    
    def _write_to_log_file(self, log_entry):
        """Write to log file with size limiting"""
        log_file = "duckhunt.log"
        max_size = 10 * 1024 * 1024  # 10MB
        
        try:
            # Check if log file exists and get its size
            if os.path.exists(log_file):
                current_size = os.path.getsize(log_file)
                
                # If file is too large, trim it by keeping only the last 5MB
                if current_size > max_size:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    # Keep only the last 50% of lines (roughly 5MB)
                    keep_lines = len(lines) // 2
                    trimmed_lines = lines[keep_lines:]
                    
                    with open(log_file, 'w', encoding='utf-8') as f:
                        f.writelines(trimmed_lines)
            
            # Append new log entry
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
                
        except Exception as e:
            # Fallback to print if file operations fail
            print(log_entry.strip())
    
    async def send_network(self, network: NetworkConnection, message):
        """Send message to IRC server for a specific network"""
        if network.sock:
            await asyncio.get_event_loop().sock_sendall(network.sock, f"{message}\r\n".encode('utf-8'))
            self.log_message("SEND", message)
    
    async def send_message(self, network: NetworkConnection, channel, message):
        """Send message to channel"""
        await self.send_network(network, f"PRIVMSG {channel} :{message}")
    
    async def send_notice(self, network: NetworkConnection, user, message):
        """Send notice to user"""
        await self.send_network(network, f"NOTICE {user} :{message}")

    def pm(self, user: str, message: str) -> str:
        """Prefix a message with the player's name as per UX convention."""
        return f"{user} - {message}"
    
    # IRC Color codes
    def colorize(self, text: str, color: str = None, bg_color: str = None, bold: bool = False) -> str:
        """Add IRC color codes to text"""
        if not color and not bg_color and not bold:
            return text
        
        codes = []
        if bold:
            codes.append('\x02')  # Bold
        if color:
            color_codes = {
                'white': '00', 'black': '01', 'blue': '02', 'green': '03', 'red': '04',
                'brown': '05', 'purple': '06', 'orange': '07', 'yellow': '08', 'lime': '09',
                'cyan': '10', 'light_cyan': '11', 'light_blue': '12', 'pink': '13', 'grey': '14', 'light_grey': '15'
            }
            if color in color_codes:
                codes.append(f'\x03{color_codes[color]}')
        if bg_color:
            bg_codes = {
                'white': '00', 'black': '01', 'blue': '02', 'green': '03', 'red': '04',
                'brown': '05', 'purple': '06', 'orange': '07', 'yellow': '08', 'lime': '09',
                'cyan': '10', 'light_cyan': '11', 'light_blue': '12', 'pink': '13', 'grey': '14', 'light_grey': '15'
            }
            if bg_color in bg_codes:
                codes.append(f',{bg_codes[bg_color]}')
        
        return ''.join(codes) + text + '\x0f'  # \x0f resets all formatting
    
    async def connect_network(self, network: NetworkConnection):
        """Connect to IRC server for a specific network"""
        server_parts = network.config['server'].split('/')
        server = server_parts[0]
        port = int(server_parts[1]) if len(server_parts) > 1 else 6667
        
        self.log_action(f"Connecting to {server}:{port} (network: {network.name})")
        
        if network.config.get('ssl', 'off').lower() == 'on':
            network.ssl_context = ssl.create_default_context()
            network.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            network.sock = network.ssl_context.wrap_socket(network.sock, server_hostname=server)
        else:
            network.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Use asyncio for non-blocking connect
        await asyncio.get_event_loop().sock_connect(network.sock, (server, port))
        # Set socket to non-blocking mode
        network.sock.setblocking(False)
        
        # Send IRC handshake
        bot_nicks = network.config['bot_nick'].split(',')
        # Remember our current nick to detect self-joins
        network.nick = bot_nicks[0]
        await self.send_network(network, f"USER DuckHuntBot 0 * :Duck Hunt Game Bot v{self.version}")
        await self.send_network(network, f"NICK {network.nick}")
    
    async def complete_registration(self, network: NetworkConnection):
        """Complete IRC registration by joining channels and running perform commands"""
        if hasattr(network, 'registration_complete'):
            return
        
        network.registration_complete = True
        self.log_action(f"Registration complete for {network.name}, joining channels and running perform commands")
        
        # Join channels
        channels = network.config['channel'].split(',')
        for channel in channels:
            channel = channel.strip()
            if channel:
                await self.send_network(network, f"JOIN {channel}")
                network.channels[channel] = set()
        
        # Perform commands
        if 'perform' in network.config:
            perform_commands = network.config['perform'].split(';')
            for cmd in perform_commands:
                if cmd.strip():
                    await self.send_network(network, cmd.strip())
        
        # Schedule first duck spawn per channel
        await self.schedule_next_duck(network)
    
    def is_owner(self, user, network: NetworkConnection = None):
        """Check if user is owner for a specific network"""
        if network:
            owners = network.config.get('owner', '').split(',')
        else:
            # Fallback to global config for backward compatibility
            owners = self.config.get('DEFAULT', 'owner', fallback='').split(',')
        return user.lower() in [o.strip().lower() for o in owners]
    
    def is_admin(self, user, network: NetworkConnection = None):
        """Check if user is admin for a specific network"""
        if network:
            admins = network.config.get('admin', '').split(',')
        else:
            # Fallback to global config for backward compatibility
            admins = self.config.get('DEFAULT', 'admin', fallback='').split(',')
        return user.lower() in [a.strip().lower() for a in admins]
    
    def is_authenticated(self, user):
        """Check if user is authenticated (cached)"""
        return user.lower() in self.authenticated_users
    
    def get_network_setting(self, network: NetworkConnection, setting: str, default=None):
        """Get a setting value for a specific network, with fallback to global config"""
        if network and setting in network.config:
            return network.config[setting]
        return self.config.get('DEFAULT', setting, fallback=default)
    
    def get_network_min_spawn(self, network: NetworkConnection):
        """Get min_spawn for a specific network"""
        return int(self.get_network_setting(network, 'min_spawn', self.min_spawn))
    
    def get_network_max_spawn(self, network: NetworkConnection):
        """Get max_spawn for a specific network"""
        return int(self.get_network_setting(network, 'max_spawn', self.max_spawn))
    
    def get_network_gold_ratio(self, network: NetworkConnection):
        """Get gold_ratio for a specific network"""
        return float(self.get_network_setting(network, 'gold_ratio', self.gold_ratio))
    
    def get_network_max_ducks(self, network: NetworkConnection):
        """Get max_ducks for a specific network"""
        return int(self.get_network_setting(network, 'max_ducks', self.max_ducks))
    
    def get_network_despawn_time(self, network: NetworkConnection):
        """Get despawn_time for a specific network"""
        return int(self.get_network_setting(network, 'despawn_time', self.despawn_time))
    
    def check_authentication(self, user):
        """Check user authentication via WHOIS"""
        if self.is_authenticated(user):
            return True
        
        # WHOIS command would need network context - for now assume authenticated
        # In a real implementation, we'd wait for WHOIS response
        # For now, we'll assume authenticated
        self.authenticated_users.add(user.lower())
        return True

    def normalize_channel(self, channel: str) -> str:
        """Normalize channel name for internal dictionaries (strip + lower)."""
        return channel.strip().lower()
    
    def get_player(self, user):
        """Get or create player data"""
        if user not in self.players:
            self.players[user] = {
                'ammo': 10,
                'magazines': 2,
                'jammed': False,
                'confiscated': False,
                'sabotaged': False,
                'inventory': {},
                'karma': 0.0,
                'channel_stats': {}  # Per-channel stats: {channel: {xp, ducks_shot, golden_ducks, misses, accidents, best_time, total_reaction_time, shots_fired, last_duck_time}}
            }
        return self.players[user]
    
    def get_channel_stats(self, user, channel):
        """Get or create channel-specific stats for a player"""
        player = self.get_player(user)
        created_new = False
        if channel not in player['channel_stats']:
            player['channel_stats'][channel] = {
                'xp': 0,
                'ducks_shot': 0,
                'golden_ducks': 0,
                'misses': 0,
                'accidents': 0,
                'best_time': None,
                'total_reaction_time': 0.0,
                'shots_fired': 0,
                'last_duck_time': None,
                'wild_fires': 0,
                'confiscated': False,
                'jammed': False,
                'sabotaged': False,
                'ammo': 0,
                'magazines': 0,
                'ap_shots': 0,
                'explosive_shots': 0,
                'bread_uses': 0,
                'befriended_ducks': 0,
                'infrared_until': 0,
                'infrared_uses': 0,
                'grease_until': 0,
                'silencer_until': 0,
                'sunglasses_until': 0,
                'ducks_detector_until': 0,
                'mirror_until': 0,
                'sand_until': 0,
                'soaked_until': 0,
                'life_insurance_until': 0,
                'liability_insurance_until': 0,
                'brush_until': 0,
                'clover_until': 0,
                'clover_bonus': 0,
                'sight_next_shot': False
            }
            created_new = True
        # Backfill newly introduced fields for existing channel stats
        stats = player['channel_stats'][channel]
        if 'ap_shots' not in stats:
            stats['ap_shots'] = 0
        if 'explosive_shots' not in stats:
            stats['explosive_shots'] = 0
        if 'bread_uses' not in stats:
            stats['bread_uses'] = 0
        if 'infrared_until' not in stats:
            stats['infrared_until'] = 0
        if 'infrared_uses' not in stats:
            stats['infrared_uses'] = 0
        if 'grease_until' not in stats:
            stats['grease_until'] = 0
        if 'silencer_until' not in stats:
            stats['silencer_until'] = 0
        if 'sunglasses_until' not in stats:
            stats['sunglasses_until'] = 0
        if 'mirror_until' not in stats:
            stats['mirror_until'] = 0
        if 'sand_until' not in stats:
            stats['sand_until'] = 0
        if 'soaked_until' not in stats:
            stats['soaked_until'] = 0
        if 'life_insurance_until' not in stats:
            stats['life_insurance_until'] = 0
        if 'liability_insurance_until' not in stats:
            stats['liability_insurance_until'] = 0
        if 'brush_until' not in stats:
            stats['brush_until'] = 0
        if 'ducks_detector_until' not in stats:
            stats['ducks_detector_until'] = 0
        if 'clover_until' not in stats:
            stats['clover_until'] = 0
        if 'clover_bonus' not in stats:
            stats['clover_bonus'] = 0
        if 'sight_next_shot' not in stats:
            stats['sight_next_shot'] = False
        if 'wild_fires' not in stats:
            stats['wild_fires'] = 0
        if 'mag_upgrade_level' not in stats:
            stats['mag_upgrade_level'] = 0
        if 'mag_capacity_level' not in stats:
            stats['mag_capacity_level'] = 0
        if 'level' not in stats:
            stats['level'] = min(50, (stats.get('xp', 0) // 100) + 1)
        # Dynamic properties will be (re)computed each fetch
        self.apply_level_bonuses(stats)
        # Initialize ammo/magazines to level-based capacities for newly created stats
        if created_new:
            stats['ammo'] = stats.get('clip_size', 10)
            stats['magazines'] = stats.get('magazines_max', 2)
        return stats

    def compute_accuracy(self, channel_stats, mode: str) -> float:
        """Compute hit chance based on level and temporary buffs.
        mode: 'shoot' or 'bef'
        """
        # Use table accuracy, then apply temporary modifiers
        props = self.get_level_properties(channel_stats['xp'])
        base = props['accuracy_pct'] / 100.0
        if mode == 'shoot' and channel_stats.get('explosive_shots', 0) > 0:
            # Explosive: Accuracy = A + (1 - A) * 0.25
            base = base + (1.0 - base) * 0.25
        # Sight next shot: increases accuracy by (1 - A) / 3, once
        if mode == 'shoot' and channel_stats.get('sight_next_shot', False):
            base = base + (1.0 - base) / 3.0
            channel_stats['sight_next_shot'] = False
        if mode == 'bef' and channel_stats.get('bread_uses', 0) > 0:
            base += 0.10  # bread improves befriending effectiveness
        # Mirror (dazzle) reduces accuracy unless sunglasses are active
        now = time.time()
        if channel_stats.get('mirror_until', 0) > now and not (channel_stats.get('sunglasses_until', 0) > now):
            # Reduce current accuracy by 25%
            base = base * 0.75
        return max(0.10, min(0.99, base))

    def get_level_properties(self, xp: int) -> dict:
        """Return level properties based on XP using the provided table."""
        thresholds = [
            (-5, 0, 55, 85, 6, 1,  -1, -1, -4),
            (-4, 1, 55, 85, 6, 2,  -1, -1, -4),
            (20, 2, 56, 86, 6, 2,  -1, -1, -4),
            (50, 3, 57, 87, 6, 2,  -1, -1, -4),
            (90, 4, 58, 88, 6, 2,  -1, -1, -4),
            (140,5, 59, 89, 6, 2,  -1, -1, -4),
            (200,6, 60, 90, 6, 2,  -1, -1, -4),
            (270,7, 65, 93, 4, 3,  -1, -1, -4),
            (350,8, 67, 93, 4, 3,  -1, -1, -4),
            (440,9, 69, 93, 4, 3,  -1, -1, -4),
            (540,10,71, 94, 4, 3,  -1, -2, -6),
            (650,11,73, 94, 4, 3,  -1, -2, -6),
            (770,12,73, 94, 4, 3,  -1, -2, -6),
            (900,13,74, 95, 4, 3,  -1, -2, -6),
            (1040,14,74,95, 4, 3,  -1, -2, -6),
            (1190,15,75,95, 4, 3,  -1, -2, -6),
            (1350,16,80,97, 2, 4,  -1, -2, -6),
            (1520,17,81,97, 2, 4,  -1, -2, -6),
            (1700,18,81,97, 2, 4,  -1, -2, -6),
            (1890,19,82,97, 2, 4,  -1, -2, -6),
            (2090,20,82,97, 2, 4,  -3, -5, -10),
            (2300,21,83,98, 2, 4,  -3, -5, -10),
            (2520,22,83,98, 2, 4,  -3, -5, -10),
            (2750,23,84,98, 2, 4,  -3, -5, -10),
            (2990,24,84,98, 2, 4,  -3, -5, -10),
            (3240,25,85,98, 2, 4,  -3, -5, -10),
            (3500,26,90,99, 1, 5,  -3, -5, -10),
            (3770,27,91,99, 1, 5,  -3, -5, -10),
            (4050,28,91,99, 1, 5,  -3, -5, -10),
            (4340,29,92,99, 1, 5,  -3, -5, -10),
            (4640,30,92,99, 1, 5,  -5, -8, -20),
            (4950,31,93,99, 1, 5,  -5, -8, -20),
            (5270,32,93,99, 1, 5,  -5, -8, -20),
            (5600,33,94,99, 1, 5,  -5, -8, -20),
            (5940,34,94,99, 1, 5,  -5, -8, -20),
            (6290,35,95,99, 1, 5,  -5, -8, -20),
            (6650,36,95,99, 1, 5,  -5, -8, -20),
            (7020,37,96,99, 1, 5,  -5, -8, -20),
            (7400,38,96,99, 1, 5,  -5, -8, -20),
            (7790,39,97,99, 1, 5,  -5, -8, -20),
            (8200,40,97,99, 1, 5,  -5, -8, -20),
        ]
        # Pick the highest threshold <= xp
        chosen = thresholds[0]
        for t in thresholds:
            if xp >= t[0]:
                chosen = t
        _, level, acc, rel, clip, clips, misspen, wildpen, accpen = chosen
        return {
            'level': level,
            'accuracy_pct': acc,
            'reliability_pct': rel,
            'clip_size': clip,
            'magazines_max': clips,
            'miss_penalty': -abs(misspen),
            'wild_penalty': -abs(wildpen),
            'accident_penalty': -abs(accpen),
        }

    async def check_level_change(self, user: str, channel: str, stats: dict, prev_xp: int, network: NetworkConnection) -> None:
        """Announce promotion/demotion when XP crosses thresholds."""
        prev_level = min(50, (prev_xp // 100) + 1)
        new_level = min(50, (stats.get('xp', 0) // 100) + 1)
        if new_level == prev_level:
            return
        titles = [
            "tourist", "noob", "duck hater", "duck hunter", "member of the Comitee Against Ducks",
            "duck pest", "duck hassler", "duck killer", "duck demolisher", "duck disassembler"
        ]
        title = titles[min(new_level-1, len(titles)-1)] if new_level > 0 else "unknown"
        if new_level > prev_level:
            await self.send_message(network, channel, self.pm(user, f"{self.colorize('PROMOTION', 'green', bold=True)}     {self.colorize(f'You are promoted to level {new_level} ({title}) in {channel}.', 'green')}"))
        else:
            await self.send_message(network, channel, self.pm(user, f"{self.colorize('DEMOTION', 'red', bold=True)}     {self.colorize(f'You are demoted to level {new_level} ({title}) in {channel}.', 'red')}"))
        stats['level'] = new_level

    def apply_level_bonuses(self, channel_stats):
        props = self.get_level_properties(channel_stats['xp'])
        # Base capacities from level table
        base_clip = props['clip_size']
        base_mags = props['magazines_max']
        # Apply player upgrades if present
        upgraded_clip = base_clip + int(channel_stats.get('mag_upgrade_level', 0))
        upgraded_mags = base_mags + int(channel_stats.get('mag_capacity_level', 0))
        channel_stats['clip_size'] = upgraded_clip
        channel_stats['magazines_max'] = upgraded_mags
        channel_stats['miss_penalty'] = props['miss_penalty']
        channel_stats['wild_penalty'] = props['wild_penalty']
        channel_stats['accident_penalty'] = props['accident_penalty']

    def unconfiscate_confiscated_in_channel(self, channel: str) -> None:
        """Quietly return confiscated guns to all players on a channel."""
        target_norm = self.normalize_channel(channel)
        for _player_name, player_data in self.players.items():
            channel_stats_map = player_data.get('channel_stats', {})
            for ch_key, stats in channel_stats_map.items():
                if self.normalize_channel(ch_key) == target_norm and stats.get('confiscated'):
                    stats['confiscated'] = False
    
    async def spawn_duck(self, network: NetworkConnection, channel=None, schedule: bool = True):
        """Spawn a new duck in a specific channel. If schedule is False, do not reset the auto timer."""
        if channel is None:
            # Pick a random channel from the network
            channels = [ch.strip() for ch in network.config.get('channel', '#default').split(',') if ch.strip()]
            if not channels:
                return
            channel = random.choice(channels)
        
        async with self.ducks_lock:
            norm_channel = self.normalize_channel(channel)
            if norm_channel not in self.active_ducks:
                self.active_ducks[norm_channel] = []
            # Enforce max_ducks from network config
            max_ducks = self.get_network_max_ducks(network)
            if len(self.active_ducks[norm_channel]) >= max_ducks:
                return
            gold_ratio = self.get_network_gold_ratio(network)
            is_golden = random.random() < gold_ratio
            duck = {
                'golden': is_golden,
                'health': 5 if is_golden else 1,
                'spawn_time': time.time(),
                'revealed': False
            }
            # Append new duck (FIFO)
            self.active_ducks[norm_channel].append(duck)
            # self.send_message(channel, f"[DEBUG] Duck added to active_ducks[{norm_channel}] - spawn_time: {duck['spawn_time']}")
            self.log_action(f"[DEBUG] Duck added to active_ducks[{norm_channel}] - spawn_time: {duck['spawn_time']}")
        
        # Debug logging
        self.log_action(f"Spawned {'golden' if is_golden else 'regular'} duck in {channel} - spawn_time: {duck['spawn_time']}")
        
        # Create duck art with custom coloring: dust=gray, duck=yellow, QUACK=red/green/gold
        dust = "-.,¸¸.-·°'`'°·-.,¸¸.-·°'`'°· "
        duck_char = "\\_O<"
        quack = "   QUACK"
        
        # Color the parts separately
        dust_colored = self.colorize(dust, 'grey')
        duck_colored = self.colorize(duck_char, 'yellow')
        quack_colored = f"   {self.colorize('Q', 'red')}{self.colorize('U', 'green')}{self.colorize('A', 'yellow')}{self.colorize('C', 'red')}{self.colorize('K', 'green')}"
        
        duck_art = f"{dust_colored}{duck_colored}{quack_colored}"
        
        await self.send_message(network, channel, duck_art)
        
        # Check active_ducks state after sending messages
        async with self.ducks_lock:
            # self.send_message(channel, f"[DEBUG] Duck stored in {channel} - spawn_time: {duck['spawn_time']}")
            self.log_action(f"Duck spawned in {channel} on {network.name} - spawn_time: {duck['spawn_time']}")
            self.log_action(f"[DEBUG] Active_ducks state after spawn: { {ch: len(lst) for ch,lst in self.active_ducks.items()} }")
        
        # Mark last spawn time for guarantees (only for automatic spawns)
        if schedule:
            try:
                network.channel_last_spawn[channel] = time.time()
            except Exception:
                pass
            await self.schedule_channel_next_duck(network, channel)
    
    async def schedule_next_duck(self, network: NetworkConnection):
        """Schedule next duck spawn for all channels on a network."""
        # Schedule each joined channel independently
        for ch in list(network.channels.keys()):
            await self.schedule_channel_next_duck(network, ch)
        # Summary for visibility
        try:
            summary = {ch: int(network.channel_next_spawn.get(ch, 0) - time.time()) for ch in network.channels.keys()}
            self.log_action(f"Per-channel schedules for {network.name} (s): {summary}")
        except Exception:
            pass

    async def schedule_channel_next_duck(self, network: NetworkConnection, channel: str, allow_immediate: bool = True):
        """Schedule next duck spawn for a specific channel with pre-notice.
        Hard guarantee: never allow gap > max_spawn; if overdue, schedule immediate
        unless allow_immediate is False (e.g., when probing via !nextduck).
        """
        now = time.time()
        last = network.channel_last_spawn.get(channel, 0)
        min_spawn = self.get_network_min_spawn(network)
        max_spawn = self.get_network_max_spawn(network)
        
        # If we've never spawned, schedule randomly within window
        if last == 0:
            spawn_delay = random.randint(min_spawn, max_spawn)
            due_time = now + spawn_delay
        else:
            # Calculate when the minimum spawn time would be satisfied
            earliest_allowed = last + min_spawn
            latest_allowed = last + max_spawn
            
            if now > latest_allowed:
                # Overdue -> normally force immediate spawn, but avoid if probing
                if allow_immediate:
                    due_time = now
                else:
                    # Set a short delay to avoid !nextduck causing an instant spawn
                    due_time = now + random.randint(10, 30)
            elif now >= earliest_allowed:
                # Minimum time has passed, schedule within remaining window
                remaining_window = max(0, int(latest_allowed - now))
                spawn_delay = random.randint(1, max(1, remaining_window))
                due_time = now + spawn_delay
            else:
                # Minimum time hasn't passed yet, wait until at least min_spawn has elapsed
                min_remaining = int(earliest_allowed - now)
                max_remaining = int(latest_allowed - now)
                spawn_delay = random.randint(min_remaining, max_remaining)
                due_time = now + spawn_delay
        network.channel_next_spawn[channel] = due_time
        network.channel_pre_notice[channel] = max(now, due_time - 60)
        network.channel_notice_sent[channel] = False
        self.log_action(f"Next duck scheduled for {channel} on {network.name} at {int(due_time - now)}s from now")

    async def can_spawn_duck(self, channel: str, network: NetworkConnection = None) -> bool:
        """Return True if the channel is below max active ducks and can accept a new duck."""
        norm_channel = self.normalize_channel(channel)
        max_ducks = self.get_network_max_ducks(network) if network else self.max_ducks
        async with self.ducks_lock:
            current_count = len(self.active_ducks.get(norm_channel, []))
            return current_count < max_ducks

    async def notify_duck_detector(self, network: NetworkConnection):
        """Notify players with an active duck detector 60s before spawn, per channel."""
        now = time.time()
        for channel in list(network.channels.keys()):
            pre = network.channel_pre_notice.get(channel)
            if pre is None:
                continue
            if not network.channel_notice_sent.get(channel, False) and now >= pre:
                # Notify each user in the channel with active detector
                for user in list(network.channels.get(channel, [])):
                    try:
                        stats = self.get_channel_stats(user, channel)
                    except Exception:
                        continue
                    until = stats.get('ducks_detector_until', 0)
                    if until and until > now:
                        # Compute seconds left to channel spawn
                        nxt = network.channel_next_spawn.get(channel)
                        seconds_left = int(nxt - now) if nxt else 60
                        seconds_left = max(0, seconds_left)
                        minutes = seconds_left // 60
                        secs = seconds_left % 60
                        msg = f"[Duck Detector] A duck will spawn in {minutes}m{secs:02d}s in {channel}."
                        await self.send_notice(network, user, msg)
                network.channel_notice_sent[channel] = True
    
    async def despawn_old_ducks(self, network: NetworkConnection = None):
        """Remove ducks that have been alive too long"""
        current_time = time.time()
        total_removed = 0
        despawn_time = self.get_network_despawn_time(network) if network else self.despawn_time
        
        # self.log_action(f"[DEBUG] despawn_old_ducks called at {current_time}")
        
        async with self.ducks_lock:
            # Debug: log despawn check (throttled to avoid flooding)
            if self.active_ducks:
                pass  # reduced debug noise
            
            # Check each channel's single active duck
            for norm_channel, ducks in list(self.active_ducks.items()):
                # Filter ducks that are still within lifespan
                remaining_ducks = []
                for duck in ducks:
                    age = current_time - duck['spawn_time']
                    if age < despawn_time:
                        remaining_ducks.append(duck)
                    else:
                        total_removed += 1
                        # Announce quiet despawn to the channel (legacy styling)
                        # Find the network for this channel to send the message
                        target_network = None
                        for net in self.networks.values():
                            if norm_channel in net.channels:
                                target_network = net
                                break
                        if target_network:
                            await self.send_message(target_network, norm_channel, self.colorize("The duck flies away.     ·°'`'°-.,¸¸.·°'`", 'grey'))
                        # Quietly unconfiscate all on this channel when a duck despawns
                        self.unconfiscate_confiscated_in_channel(norm_channel)
                        # Update last spawn time for this channel
                        if target_network:
                            target_network.channel_last_spawn[norm_channel] = current_time
                if remaining_ducks:
                    self.active_ducks[norm_channel] = remaining_ducks
                else:
                    del self.active_ducks[norm_channel]
    
    async def handle_bang(self, user, channel, network: NetworkConnection):
        """Handle !bang command"""
        if not self.check_authentication(user):
            await self.send_message(network, channel, self.pm(user, "You must be authenticated to play."))
            return
        
        player = self.get_player(user)
        channel_stats = self.get_channel_stats(user, channel)
        
        if channel_stats['confiscated']:
            # self.send_message(channel, f"[DEBUG] Early return: confiscated=True")
            await self.send_message(network, channel, self.pm(user, "You are not armed."))
            return
        
        if channel_stats['jammed']:
            # self.send_message(channel, f"[DEBUG] Early return: jammed=True")
            clip_size = channel_stats.get('clip_size', 10)
            mags_max = channel_stats.get('magazines_max', 2)
            await self.send_message(network, channel, self.pm(user, f"{self.colorize('*CLACK*', 'red', bold=True)}     {self.colorize('Your gun is jammed, you must reload to unjam it...', 'red')} | Ammo: {channel_stats['ammo']}/{clip_size} | Magazines : {channel_stats['magazines']}/{mags_max}"))
            return
        
        if channel_stats['ammo'] <= 0:
            # self.send_message(channel, f"[DEBUG] Early return: ammo={channel_stats['ammo']}")
            clip_size = channel_stats.get('clip_size', 10)
            mags_max = channel_stats.get('magazines_max', 2)
            await self.send_message(network, channel, self.pm(user, f"*CLICK*     EMPTY MAGAZINE | Ammo: 0/{clip_size} | Magazines: {channel_stats['magazines']}/{mags_max}"))
            return
        
        # Check if there is a duck in this channel
        async with self.ducks_lock:
            norm_channel = self.normalize_channel(channel)
            # self.send_message(channel, f"[DEBUG] Bang check - all channels: {list(self.active_ducks.keys())}")
            # self.send_message(channel, f"[DEBUG] Bang check - channel in ducks: {norm_channel in self.active_ducks}")
            if norm_channel not in self.active_ducks:
                # Infrared Detector: if active AND has uses, allow safe trigger lock and consume one use
                now = time.time()
                if channel_stats.get('infrared_until', 0) > now and channel_stats.get('infrared_uses', 0) > 0:
                    channel_stats['infrared_uses'] = max(0, channel_stats.get('infrared_uses', 0) - 1)
                    remaining_uses = channel_stats.get('infrared_uses', 0)
                    await self.send_message(network, channel, self.pm(user, f"*CLICK*     Trigger locked. [{remaining_uses} remaining]"))
                    self.save_player_data()
                    return
                # No duck present - apply wild fire penalties and confiscation
                miss_pen = -random.randint(1, 5)  # Random penalty (-1 to -5) on miss
                wild_pen = -2
                if channel_stats.get('liability_insurance_until', 0) > now:
                    # Liability insurance should only reduce accident-related penalties (wildfire/ricochet), not plain miss
                    if wild_pen < 0:
                        wild_pen = math.floor(wild_pen / 2)
                total_pen = miss_pen + wild_pen
                channel_stats['confiscated'] = True
                prev_xp = channel_stats['xp']
                channel_stats['xp'] = max(0, channel_stats['xp'] + total_pen)
                channel_stats['wild_fires'] += 1
                await self.send_message(network, channel, self.pm(user, f"{self.colorize('Luckily you missed, but what did you aim at ? There is no duck in the area...', 'red')}   {self.colorize(f'[missed: {miss_pen} xp]', 'red')} {self.colorize(f'[wild fire: {wild_pen} xp]', 'red')}   {self.colorize('[GUN CONFISCATED: wild fire]', 'red', bold=True)}"))
                # Accidental shooting (wild fire): 50% chance to hit a random player
                victim = None
                if channel in network.channels and network.channels[channel]:
                    candidates = [u for u in list(network.channels[channel]) if u != user]
                    try:
                        bot_nick = self.config['bot_nick'].split(',')[0]
                        candidates = [u for u in candidates if u != bot_nick]
                    except Exception:
                        pass
                    if candidates and random.random() < 0.50:
                        victim = random.choice(candidates)
                if victim:
                    acc_pen = channel_stats.get('accident_penalty', -4)
                    if channel_stats.get('liability_insurance_until', 0) > now and acc_pen < 0:
                        acc_pen = math.floor(acc_pen / 2)
                    channel_stats['accidents'] += 1
                    channel_stats['xp'] = max(0, channel_stats['xp'] + acc_pen)
                    insured = channel_stats.get('life_insurance_until', 0) > now
                    if insured:
                        channel_stats['confiscated'] = False
                    # Mirror on victim can add extra penalty if shooter lacks sunglasses
                    vstats = self.get_channel_stats(victim, channel)
                    if vstats.get('mirror_until', 0) > now and not (channel_stats.get('sunglasses_until', 0) > now):
                        extra = -1
                        if channel_stats.get('liability_insurance_until', 0) > now:
                            extra = math.floor(extra / 2)
                        channel_stats['xp'] = max(0, channel_stats['xp'] + extra)
                        await self.send_message(network, channel, self.pm(user, f"ACCIDENT     You accidentally shot {victim}! [accident: {acc_pen} xp] [mirror glare: {extra} xp]{' [INSURED: no confiscation]' if insured else ''}"))
                    else:
                        await self.send_message(network, channel, self.pm(user, f"ACCIDENT     You accidentally shot {victim}! [accident: {acc_pen} xp]{' [INSURED: no confiscation]' if insured else ''}"))
                await self.check_level_change(user, channel, channel_stats, prev_xp, network)
                self.save_player_data()
                return
            
            # Target the active duck in this channel
            target_duck = self.active_ducks[norm_channel][0]
            
            # Get channel-specific stats
            channel_stats = self.get_channel_stats(user, channel)
            
            # Reliability (jam) check before consuming ammo
            props = self.get_level_properties(channel_stats['xp'])
            reliability = props['reliability_pct'] / 100.0
            # Grease halves jam odds while active
            if channel_stats.get('grease_until', 0) > time.time():
                reliability = 1.0 - (1.0 - reliability) * 0.5
            # Sand makes jams more likely (halve reliability)
            if channel_stats.get('sand_until', 0) > time.time():
                reliability = reliability * 0.5
            # Brush slightly improves reliability while active (+10% of remaining)
            if channel_stats.get('brush_until', 0) > time.time():
                reliability = reliability + (1.0 - reliability) * 0.10
            if random.random() > reliability:
                channel_stats['jammed'] = True
                clip_size = channel_stats.get('clip_size', 10)
                mags_max = channel_stats.get('magazines_max', 2)
                await self.send_message(network, channel, self.pm(user, f"{self.colorize('*CLACK*', 'red', bold=True)}     {self.colorize('Your gun is jammed, you must reload to unjam it...', 'red')} | Ammo: {channel_stats['ammo']}/{clip_size} | Magazines : {channel_stats['magazines']}/{mags_max}"))
                self.save_player_data()
                return

            # Shoot at duck (consume ammo on non-jam)
            channel_stats['ammo'] -= 1
            channel_stats['shots_fired'] += 1
            reaction_time = time.time() - target_duck['spawn_time']
            
            # Accuracy check
            hit_roll = random.random()
            hit_chance = self.compute_accuracy(channel_stats, 'shoot')
            # Soaked players cannot shoot
            if channel_stats.get('soaked_until', 0) > time.time():
                await self.send_message(network, channel, self.pm(user, "You are soaked and cannot shoot. Use spare clothes or wait."))
                return
            if hit_roll > hit_chance:
                channel_stats['shots_fired'] += 1
                channel_stats['misses'] += 1
                # Random penalty (-1 to -5) on miss
                penalty = -random.randint(1, 5)
                prev_xp = channel_stats['xp']
                channel_stats['xp'] = max(0, channel_stats['xp'] + penalty)
                await self.send_message(network, channel, self.pm(user, f"{self.colorize('*BANG*', 'red', bold=True)}     {self.colorize('You missed.', 'red')} {self.colorize(f'[{penalty} xp]', 'red')}"))
                # Ricochet accident: 20% chance to hit a random player
                victim = None
                if channel in network.channels and network.channels[channel]:
                    candidates = [u for u in list(network.channels[channel]) if u != user]
                    try:
                        bot_nick = self.config['bot_nick'].split(',')[0]
                        candidates = [u for u in candidates if u != bot_nick]
                    except Exception:
                        pass
                    if candidates and random.random() < 0.20:
                        victim = random.choice(candidates)
                if victim:
                    now2 = time.time()
                    acc_pen = channel_stats.get('accident_penalty', -4)
                    if channel_stats.get('liability_insurance_until', 0) > now2 and acc_pen < 0:
                        acc_pen = math.floor(acc_pen / 2)
                    channel_stats['accidents'] += 1
                    channel_stats['xp'] = max(0, channel_stats['xp'] + acc_pen)
                    insured = channel_stats.get('life_insurance_until', 0) > now2
                    if insured:
                        channel_stats['confiscated'] = False
                    else:
                        channel_stats['confiscated'] = True
                    vstats = self.get_channel_stats(victim, channel)
                    if vstats.get('mirror_until', 0) > now2 and not (channel_stats.get('sunglasses_until', 0) > now2):
                        extra = -1
                        if channel_stats.get('liability_insurance_until', 0) > now2:
                            extra = math.floor(extra / 2)
                        channel_stats['xp'] = max(0, channel_stats['xp'] + extra)
                        await self.send_message(network, channel, self.pm(user, f"{self.colorize('ACCIDENT', 'red', bold=True)}     {self.colorize('Your bullet ricochets into', 'red')} {victim}! {self.colorize(f'[accident: {acc_pen} xp]', 'red')} {self.colorize(f'[mirror glare: {extra} xp]', 'purple')}{self.colorize(' [INSURED: no confiscation]', 'green') if insured else self.colorize(' [GUN CONFISCATED: accident]', 'red', bold=True)}"))
                    else:
                        await self.send_message(network, channel, self.pm(user, f"{self.colorize('ACCIDENT', 'red', bold=True)}     {self.colorize('Your bullet ricochets into', 'red')} {victim}! {self.colorize(f'[accident: {acc_pen} xp]', 'red')}{self.colorize(' [INSURED: no confiscation]', 'green') if insured else self.colorize(' [GUN CONFISCATED: accident]', 'red', bold=True)}"))
                await self.check_level_change(user, channel, channel_stats, prev_xp, network)
                self.save_player_data()
                return

            # Compute damage
            damage = 1
            if target_duck['golden']:
                if channel_stats.get('explosive_shots', 0) > 0:
                    damage = 2
                    channel_stats['explosive_shots'] = max(0, channel_stats['explosive_shots'] - 1)
                elif channel_stats.get('ap_shots', 0) > 0:
                    damage = 2
                    channel_stats['ap_shots'] = max(0, channel_stats['ap_shots'] - 1)
            
            target_duck['health'] -= damage
            duck_killed = target_duck['health'] <= 0
            
            # Reveal golden duck on first hit
            if target_duck['golden'] and not target_duck.get('revealed', False):
                target_duck['revealed'] = True
                # Add golden duck message to the same line as the hit message
                hit_msg = f"{self.colorize('*BANG*', 'red', bold=True)}     {self.colorize('You hit the duck!', 'orange')} {self.colorize('(* GOLDEN DUCK DETECTED *)', 'yellow', bold=True)}"
                await self.send_message(network, channel, self.pm(user, hit_msg))
                return
            
            # Remove if dead
            if duck_killed and norm_channel in self.active_ducks:
                # Remove the first (oldest) duck
                if self.active_ducks[norm_channel]:
                    self.active_ducks[norm_channel].pop(0)
                if not self.active_ducks[norm_channel]:
                    del self.active_ducks[norm_channel]
                # Quietly unconfiscate all on this channel
                self.unconfiscate_confiscated_in_channel(channel)
            channel_stats['ducks_shot'] += 1
            channel_stats['last_duck_time'] = time.time()  # Record when duck was shot
            if duck_killed:
                # Only record when duck is actually killed
                self.channel_last_duck_time[norm_channel] = time.time()
                # Base XP for kill (golden vs regular)
                if target_duck['golden']:
                    channel_stats['golden_ducks'] += 1
                    base_xp = 50
                else:
                    base_xp = int(self.config.get('DEFAULT', 'default_xp', fallback=10))

                # Apply clover bonus if active (affects both golden and regular)
                if channel_stats.get('clover_until', 0) > time.time():
                    xp_gain = base_xp + int(channel_stats.get('clover_bonus', 0))
                else:
                    xp_gain = base_xp
            else:
                xp_gain = 0
            
            prev_xp = channel_stats['xp']
            channel_stats['xp'] += xp_gain
            channel_stats['total_reaction_time'] += reaction_time
            
            if not channel_stats['best_time'] or reaction_time < channel_stats['best_time']:
                channel_stats['best_time'] = reaction_time
            
            # Check for level up (based on channel XP)
            new_level = min(50, (channel_stats['xp'] // 100) + 1)
        # Build item display string
        item_display = ""
        if 'inventory' in player and player['inventory']:
            item_list = []
            for item, count in player['inventory'].items():
                if count > 0:
                    item_list.append(f"{item} x{count}")
            if item_list:
                item_display = f" [{', '.join(item_list)}]"
        
        # Level is now per-channel, but we'll use a simple calculation for display
        current_channel_level = min(50, (channel_stats['xp'] // 100) + 1)
        
        if new_level > current_channel_level:
            level_titles = ["tourist", "noob", "duck hater", "duck hunter", "member of the Comitee Against Ducks", 
                          "duck pest", "duck hassler", "duck killer", "duck demolisher", "duck disassembler"]
            title = level_titles[min(new_level-1, len(level_titles)-1)]
            await self.send_message(network, channel, self.pm(user, f"{self.colorize('*BANG*', 'red', bold=True)}     {self.colorize('You shot down the duck', 'green', bold=True)} in {reaction_time:.3f}s, which makes you a total of {channel_stats['ducks_shot']} ducks on {channel}. You are promoted to level {new_level} ({title}).     {self.colorize('\\_X<   *KWAK*', 'red')}   {self.colorize(f'[{xp_gain} xp]', 'green')}{item_display}"))
        else:
            if duck_killed:
                sign = '+' if xp_gain > 0 else ''
                await self.send_message(network, channel, self.pm(user, f"{self.colorize('*BANG*', 'red', bold=True)}     {self.colorize('You shot down the duck', 'green', bold=True)} in {reaction_time:.3f}s, which makes you a total of {channel_stats['ducks_shot']} ducks on {channel}.     {self.colorize('\\_X<   *KWAK*', 'red')}   {self.colorize(f'[{sign}{xp_gain} xp]', 'green')}{item_display}"))
            else:
                remaining = max(0, target_duck['health'])
                if target_duck['golden']:
                    await self.send_message(network, channel, self.pm(user, f"{self.colorize('*BANG*', 'red', bold=True)}     {self.colorize('The golden duck survived ! Try again.', 'yellow', bold=True)}   {self.colorize('\\_O<', 'yellow')}  {self.colorize(f'[life -{damage}]', 'red')}"))
                else:
                    await self.send_message(network, channel, self.pm(user, f"{self.colorize('*BANG*', 'red', bold=True)}     {self.colorize('You hit the duck!', 'orange')} Remaining health: {remaining}."))
        # Announce promotion/demotion if level changed (any XP change path)
        if xp_gain != 0:
            await self.check_level_change(user, channel, channel_stats, prev_xp, network)
        
        # Random weighted loot drop (10% chance) on kill only
        if duck_killed and random.random() < 0.10:
            await self.apply_weighted_loot(user, channel, channel_stats, network)
        
        self.save_player_data()
        await self.schedule_next_duck(network)
    
    async def handle_bef(self, user, channel, network: NetworkConnection):
        """Handle !bef (befriend) command"""
        if not self.check_authentication(user):
            await self.send_message(network, channel, self.pm(user, "You must be authenticated to play."))
            return
        
        player = self.get_player(user)
        channel_stats = self.get_channel_stats(user, channel)
        
        # Check if there is a duck in this channel
        async with self.ducks_lock:
            norm_channel = self.normalize_channel(channel)
            # self.send_message(channel, f"[DEBUG] Bef check - all channels: {list(self.active_ducks.keys())}")
            # self.send_message(channel, f"[DEBUG] Bef check - channel in ducks: {norm_channel in self.active_ducks}")
            if norm_channel not in self.active_ducks:
                self.log_action(f"No ducks to befriend in {channel} - active_ducks keys: {list(self.active_ducks.keys())}")
                # Apply random penalty (-1 to -10) for befriending when no ducks are present
                penalty = -random.randint(1, 10)
                channel_stats['xp'] = max(0, channel_stats['xp'] + penalty)
                await self.send_message(network, channel, self.pm(user, f"{self.colorize('There are no ducks to befriend.', 'red')} {self.colorize(f'[{penalty} XP]', 'red')}"))
                self.save_player_data()
                return
            
            # Get the active duck
            duck = self.active_ducks[norm_channel][0]
            
            # Accuracy-style check for befriending (duck might not notice)
            bef_roll = random.random()
            bef_chance = self.compute_accuracy(channel_stats, 'bef')
            if channel_stats.get('soaked_until', 0) > time.time():
                await self.send_message(network, channel, self.pm(user, "You are soaked and cannot befriend. Use spare clothes or wait."))
                return
            if bef_roll > bef_chance:
                # Random penalty (-1 to -10) on failed befriend (duck distracted)
                penalty = -random.randint(1, 10)
                channel_stats['misses'] += 1
                channel_stats['xp'] = max(0, channel_stats['xp'] + penalty)
                await self.send_message(network, channel, self.pm(user, f"FRIEND     The duck seems distracted. Try again. [{penalty} XP]"))
                self.save_player_data()
                return

            # Compute befriend effectiveness
            bef_damage = 1
            if duck['golden'] and channel_stats.get('bread_uses', 0) > 0:
                bef_damage = 2
                channel_stats['bread_uses'] = max(0, channel_stats['bread_uses'] - 1)
            
            duck['health'] -= bef_damage
            bef_killed = duck['health'] <= 0
            
            # Reveal golden duck on first befriend attempt
            if duck['golden'] and not duck.get('revealed', False):
                duck['revealed'] = True
                # Add golden duck message to the same line as the befriend message
                bef_msg = f"{self.colorize('\\_0< QUAACK!', 'green')} {self.colorize(f'[BEFRIENDED DUCKS: {channel_stats['befriended_ducks']}]', 'green')} {self.colorize(f'[+{xp_gained} xp]', 'green')} {self.colorize('(* GOLDEN DUCK DETECTED *)', 'yellow', bold=True)}"
                await self.send_message(network, channel, self.pm(user, bef_msg))
                return
            
            # Remove the duck if fully befriended
            if bef_killed:
                # Remove FIFO
                if self.active_ducks[norm_channel]:
                    self.active_ducks[norm_channel].pop(0)
                if not self.active_ducks[norm_channel]:
                    del self.active_ducks[norm_channel]
                # Quietly unconfiscate all on this channel
                self.unconfiscate_confiscated_in_channel(channel)
        
        # Award XP for befriending when completed
        if bef_killed:
            # Base XP for befriending (golden vs regular)
            base_xp = 50 if duck['golden'] else int(self.config.get('DEFAULT', 'default_xp', fallback=10))
            # Four-leaf clover bonus if active
            if channel_stats.get('clover_until', 0) > time.time():
                xp_gained = base_xp + int(channel_stats.get('clover_bonus', 0))
            else:
                xp_gained = base_xp
            prev_xp = channel_stats['xp']
            channel_stats['xp'] += xp_gained
            channel_stats['befriended_ducks'] += 1
            response = f"FRIEND     The "
            if duck['golden']:
                response += "GOLDEN DUCK"
            else:
                response += "DUCK"
            response += f" was befriended!   {self.colorize('\\_0< QUAACK!', 'green')}   {self.colorize(f'[BEFRIENDED DUCKS: {channel_stats['befriended_ducks']}]', 'green')} {self.colorize(f'[+{xp_gained} xp]', 'green')}"
            await self.send_message(network, channel, self.pm(user, response))
            self.log_action(f"{user} befriended a {'golden ' if duck['golden'] else ''}duck in {channel}")
            await self.check_level_change(user, channel, channel_stats, prev_xp, network)
        else:
            remaining = max(0, duck['health'])
            await self.send_message(network, channel, self.pm(user, f"{self.colorize('FRIEND', 'green', bold=True)}     {self.colorize('You comfort the duck.', 'green')} Remaining friendliness needed: {remaining}."))
        
        self.save_player_data()
        await self.schedule_next_duck(network)
    
    async def handle_reload(self, user, channel, network: NetworkConnection):
        """Handle !reload command"""
        if not self.check_authentication(user):
            return
        
        player = self.get_player(user)
        channel_stats = self.get_channel_stats(user, channel)
        
        if channel_stats['confiscated']:
            await self.send_message(network, channel, self.pm(user, "You are not armed."))
            return
        
        # Only allow reload if out of bullets, jammed, or sabotaged
        if channel_stats['jammed']:
            channel_stats['jammed'] = False
            clip_size = channel_stats.get('clip_size', 10)
            mags_max = channel_stats.get('magazines_max', 2)
            await self.send_message(network, channel, self.pm(user, f"*Crr..CLICK*     You unjam your gun. | Ammo: {channel_stats['ammo']}/{clip_size} | Magazines: {channel_stats['magazines']}/{mags_max}"))
        elif channel_stats['sabotaged']:
            channel_stats['sabotaged'] = False
            clip_size = channel_stats.get('clip_size', 10)
            mags_max = channel_stats.get('magazines_max', 2)
            await self.send_message(network, channel, self.pm(user, f"*Crr..CLICK*     You fix the sabotage. | Ammo: {channel_stats['ammo']}/{clip_size} | Magazines: {channel_stats['magazines']}/{mags_max}"))
        elif channel_stats['ammo'] == 0:
            if channel_stats['magazines'] <= 0:
                await self.send_message(network, channel, self.pm(user, "You have no magazines left to reload with."))
            else:
                clip_size = channel_stats.get('clip_size', 10)
                channel_stats['ammo'] = clip_size
                channel_stats['magazines'] -= 1
                mags_max = channel_stats.get('magazines_max', 2)
                await self.send_message(network, channel, self.pm(user, f"{self.colorize('*CLACK CLACK*', 'blue', bold=True)}     {self.colorize('You reload.', 'blue')} | Ammo: {channel_stats['ammo']}/{clip_size} | Magazines: {channel_stats['magazines']}/{mags_max}"))
        else:
            clip_size = channel_stats.get('clip_size', 10)
            mags_max = channel_stats.get('magazines_max', 2)
            await self.send_message(network, channel, self.pm(user, f"{self.colorize('Your gun doesn\'t need to be reloaded.', 'grey')} | Ammo: {channel_stats['ammo']}/{clip_size} | Magazines: {channel_stats['magazines']}/{mags_max}"))
        
        self.save_player_data()
    
    async def handle_shop(self, user, channel, args, network: NetworkConnection):
        """Handle !shop command"""
        if not self.check_authentication(user):
            return
        
        if not args:
            # Show shop menu (split into multiple messages due to IRC length limits)
            await self.send_notice(network, user, "[Duck Hunt] Purchasable items:")
            
            # Group items into chunks that fit IRC message limits
            items = []
            for item_id, item in self.shop_items.items():
                # Dynamic costs for upgrades (22/23) are per-player based on current level
                if item_id == 22:
                    lvl = self.get_channel_stats(user, channel).get('mag_upgrade_level', 0)
                    dyn_cost = min(1000, 200 * (lvl + 1))
                    items.append(f"{item_id}- {item['name']} ({dyn_cost} xp)")
                elif item_id == 23:
                    lvl = self.get_channel_stats(user, channel).get('mag_capacity_level', 0)
                    dyn_cost = min(1000, 200 * (lvl + 1))
                    items.append(f"{item_id}- {item['name']} ({dyn_cost} xp)")
                else:
                    items.append(f"{item_id}- {item['name']} ({item['cost']} xp)")
            
            # Split into chunks of ~400 characters each
            current_chunk = ""
            for item in items:
                if len(current_chunk + " | " + item) > 400:
                    if current_chunk:
                        await self.send_notice(network, user, current_chunk)
                    current_chunk = item
                else:
                    if current_chunk:
                        current_chunk += " | " + item
                    else:
                        current_chunk = item
            
            if current_chunk:
                await self.send_notice(network, user, current_chunk)
            
            await self.send_notice(network, user, "Syntax: !shop [id [target]]")
        else:
            # Handle purchase
            try:
                item_id = int(args[0])
                if item_id not in self.shop_items:
                    await self.send_notice(network, user, "Invalid item ID.")
                    return
                
                player = self.get_player(user)
                channel_stats = self.get_channel_stats(user, channel)
                item = self.shop_items[item_id]
                # Determine dynamic cost for upgrades
                cost = item['cost']
                if item_id == 22:
                    lvl = channel_stats.get('mag_upgrade_level', 0)
                    cost = min(1000, 200 * (lvl + 1))
                elif item_id == 23:
                    lvl = channel_stats.get('mag_capacity_level', 0)
                    cost = min(1000, 200 * (lvl + 1))
                if channel_stats['xp'] < cost:
                    await self.send_notice(network, user, f"You don't have enough XP in {channel}. You need {cost} xp.")
                    return
                prev_xp = channel_stats['xp']
                channel_stats['xp'] -= cost
                
                # Apply item effects
                if item_id == 1:  # Extra bullet
                    clip_size = channel_stats.get('clip_size', 10)
                    if channel_stats['ammo'] < clip_size:
                        channel_stats['ammo'] = min(clip_size, channel_stats['ammo'] + 1)
                        await self.send_message(network, channel, self.pm(user, f"You just added an extra bullet. [-{cost} XP] | Ammo: {channel_stats['ammo']}/{clip_size}"))
                    else:
                        await self.send_message(network, channel, self.pm(user, f"Your magazine is already full."))
                        channel_stats['xp'] += item['cost']  # Refund XP
                elif item_id == 2:  # Extra magazine
                    mags_max = channel_stats.get('magazines_max', 2)
                    if channel_stats['magazines'] < mags_max:
                        channel_stats['magazines'] = min(mags_max, channel_stats['magazines'] + 1)
                        await self.send_message(network, channel, self.pm(user, f"You just added an extra magazine. [-{cost} XP] | Magazines: {channel_stats['magazines']}/{mags_max}"))
                    else:
                        await self.send_message(network, channel, self.pm(user, f"You already have the maximum magazines."))
                        channel_stats['xp'] += item['cost']  # Refund XP
                elif item_id == 3:  # AP ammo: next 20 shots do +1 dmg vs golden (i.e., 2 total)
                    ap = channel_stats.get('ap_shots', 0)
                    ex = channel_stats.get('explosive_shots', 0)
                    if ap > 0 and ex == 0:
                        await self.send_notice(network, user, "AP ammo already active. Use it up before buying more.")
                        channel_stats['xp'] += item['cost']
                    else:
                        switched = ex > 0
                        channel_stats['explosive_shots'] = 0
                        channel_stats['ap_shots'] = 20
                        if switched:
                            await self.send_message(network, channel, self.pm(user, f"You switched to AP ammo. Next 20 shots are AP. [-{cost} XP]"))
                        else:
                            await self.send_message(network, channel, self.pm(user, f"{self.colorize('You purchased AP ammo.', 'green')} Next 20 shots deal extra damage to golden ducks. {self.colorize(f'[-{cost} XP]', 'red')}"))
                elif item_id == 4:  # Explosive ammo: next 20 shots do +1 dmg vs golden and boost accuracy
                    ap = channel_stats.get('ap_shots', 0)
                    ex = channel_stats.get('explosive_shots', 0)
                    if ex > 0 and ap == 0:
                        await self.send_notice(network, user, "Explosive ammo already active. Use it up before buying more.")
                        channel_stats['xp'] += item['cost']
                    else:
                        switched = ap > 0
                        channel_stats['ap_shots'] = 0
                        channel_stats['explosive_shots'] = 20
                        if switched:
                            await self.send_message(network, channel, self.pm(user, f"You switched to explosive ammo. Next 20 shots are explosive. [-{cost} XP]"))
                        else:
                            await self.send_message(network, channel, self.pm(user, f"{self.colorize('You purchased explosive ammo.', 'green')} Next 20 shots deal extra damage to golden ducks. {self.colorize(f'[-{cost} XP]', 'red')}"))
                elif item_id == 6:  # Grease: 24h reliability boost
                    now = time.time()
                    duration = 24 * 3600
                    if channel_stats.get('grease_until', 0) > now:
                        await self.send_notice(network, user, "Grease already applied. Wait until it wears off to buy more.")
                        channel_stats['xp'] += item['cost']
                    else:
                        channel_stats['grease_until'] = now + duration
                        await self.send_message(network, channel, self.pm(user, f"{self.colorize('You purchased grease.', 'green')} Your gun will jam half as often for 24h. {self.colorize(f'[-{cost} XP]', 'red')}"))
                elif item_id == 7:  # Sight: next shot accuracy boost; cannot stack
                    if channel_stats.get('sight_next_shot', False):
                        await self.send_notice(network, user, "Sight already mounted for your next shot. Use it before buying more.")
                        channel_stats['xp'] += item['cost']
                    else:
                        channel_stats['sight_next_shot'] = True
                        await self.send_message(network, channel, self.pm(user, f"{self.colorize('You purchased a sight.', 'green')} Your next shot will be more accurate. {self.colorize(f'[-{cost} XP]', 'red')}"))
                elif item_id == 11:  # Sunglasses: 24h protection against mirror / reduce accident penalty
                    channel_stats['sunglasses_until'] = max(channel_stats.get('sunglasses_until', 0), time.time() + 24*3600)
                    await self.send_message(network, channel, self.pm(user, f"You put on sunglasses for 24h. You're protected against mirror glare. [-{cost} XP]"))
                elif item_id == 12:  # Spare clothes: clear soaked if present
                    if channel_stats.get('soaked_until', 0) > time.time():
                        channel_stats['soaked_until'] = 0
                        await self.send_message(network, channel, self.pm(user, f"You change into spare clothes. You're no longer soaked. [-{cost} XP]"))
                    else:
                        await self.send_notice(network, user, "You're not soaked. Refunding XP.")
                        channel_stats['xp'] += item['cost']
                elif item_id == 13:  # Brush for gun: unjam, clear sand, and small reliability buff for 24h
                    channel_stats['jammed'] = False
                    # Clear sand debuff if present
                    if channel_stats.get('sand_until', 0) > time.time():
                        channel_stats['sand_until'] = 0
                    channel_stats['brush_until'] = max(channel_stats.get('brush_until', 0), time.time() + 24*3600)
                    await self.send_message(network, channel, self.pm(user, f"You clean your gun and remove sand. It feels smoother for 24h. [-{cost} XP]"))
                elif item_id == 14:  # Mirror: apply dazzle debuff to target unless countered by sunglasses (target required)
                    if len(args) < 2:
                        await self.send_notice(network, user, "Usage: !shop 14 <nick>")
                        channel_stats['xp'] += item['cost']
                    else:
                        target = args[1]
                        tstats = self.get_channel_stats(target, channel)
                        # If target has sunglasses active, mirror is countered
                        if tstats.get('sunglasses_until', 0) > time.time():
                            await self.send_message(network, channel, self.pm(user, f"{target} is wearing sunglasses. The mirror has no effect."))
                            channel_stats['xp'] += item['cost']
                        else:
                            tstats['mirror_until'] = max(tstats.get('mirror_until', 0), time.time() + 24*3600)
                            await self.send_message(network, channel, self.pm(user, f"You dazzle {target} with a mirror for 24h. Their accuracy is reduced. [-{cost} XP]"))
                elif item_id == 15:  # Handful of sand: victim reliability worse for 1h (target required)
                    if len(args) < 2:
                        await self.send_notice(network, user, "Usage: !shop 15 <nick>")
                        channel_stats['xp'] += item['cost']
                    else:
                        target = args[1]
                        tstats = self.get_channel_stats(target, channel)
                        tstats['sand_until'] = max(tstats.get('sand_until', 0), time.time() + 3600)
                        await self.send_message(network, channel, self.pm(user, f"You throw sand into {target}'s gun. Their gun will jam more for 1h. [-{cost} XP]"))
                elif item_id == 16:  # Water bucket: soak target for 1h (target required)
                    if len(args) < 2:
                        await self.send_notice(network, user, "Usage: !shop 16 <nick>")
                        channel_stats['xp'] += item['cost']
                    else:
                        target = args[1]
                        tstats = self.get_channel_stats(target, channel)
                        tstats['soaked_until'] = max(tstats.get('soaked_until', 0), time.time() + 3600)
                        await self.send_message(network, channel, self.pm(user, f"You soak {target} with a water bucket. They're out for 1h unless they change clothes. [-{cost} XP]"))
                elif item_id == 17:  # Sabotage: jam target immediately (target required)
                    if len(args) < 2:
                        await self.send_notice(network, user, "Usage: !shop 17 <nick>")
                        channel_stats['xp'] += item['cost']
                    else:
                        target = args[1]
                        tstats = self.get_channel_stats(target, channel)
                        tstats['jammed'] = True
                        await self.send_message(network, channel, self.pm(user, f"You sabotage {target}'s weapon. It's jammed. [-{cost} XP]"))
                elif item_id == 18:  # Life insurance: protect against confiscation for 24h
                    channel_stats['life_insurance_until'] = max(channel_stats.get('life_insurance_until', 0), time.time() + 24*3600)
                    await self.send_message(network, channel, self.pm(user, f"You purchase life insurance. Confiscations will be prevented for 24h. [-{cost} XP]"))
                elif item_id == 19:  # Liability insurance: reduce penalties by 50% for 24h
                    channel_stats['liability_insurance_until'] = max(channel_stats.get('liability_insurance_until', 0), time.time() + 24*3600)
                    await self.send_message(network, channel, self.pm(user, f"You purchase liability insurance. Penalties reduced by 50% for 24h. [-{cost} XP]"))
                elif item_id == 22:  # Upgrade Magazine: increase clip size (level 1-5), dynamic cost per level
                    current_level = channel_stats.get('mag_upgrade_level', 0)
                    if current_level >= 5:
                        await self.send_message(network, channel, self.pm(user, "Your magazine is already fully upgraded."))
                        channel_stats['xp'] += cost
                    else:
                        next_level = current_level + 1
                        channel_stats['mag_upgrade_level'] = next_level
                        # Recompute clip_size via level bonuses so upgrades stack correctly
                        self.apply_level_bonuses(channel_stats)
                        # Top off ammo by 1 up to new clip size
                        channel_stats['ammo'] = min(channel_stats['clip_size'], channel_stats['ammo'] + 1)
                        await self.send_message(network, channel, self.pm(user, f"Upgrade applied. Magazine capacity increased to {channel_stats['clip_size']}. [-{cost} XP]"))
                elif item_id == 10:  # Four-leaf clover: +N XP per duck for 24h; single active at a time
                    now = time.time()
                    duration = 24 * 3600
                    if channel_stats.get('clover_until', 0) > now:
                        # Already active; refund
                        await self.send_notice(network, user, "Four-leaf clover already active. Wait until it expires to buy again.")
                        channel_stats['xp'] += item['cost']
                    else:
                        bonus = random.choice([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
                        channel_stats['clover_bonus'] = bonus
                        channel_stats['clover_until'] = now + duration
                        await self.send_message(network, channel, self.pm(user, f"Four-leaf clover activated for 24h. +{bonus} XP per duck. [-{cost} XP]"))
                elif item_id == 8:  # Infrared detector: 24h trigger lock window when no duck, limited uses
                    now = time.time()
                    duration = 24 * 3600
                    # Disallow purchase if active and has uses remaining
                    if channel_stats.get('infrared_until', 0) > now and channel_stats.get('infrared_uses', 0) > 0:
                        await self.send_notice(network, user, "Infrared detector already active. Use it up before buying more.")
                        channel_stats['xp'] += item['cost']
                    else:
                        new_until = now + duration
                        channel_stats['infrared_until'] = new_until
                        channel_stats['infrared_uses'] = 6
                        hours = duration // 3600
                        await self.send_message(network, channel, self.pm(user, f"Infrared detector enabled for {hours}h00m. Trigger lock has 6 uses. [-{cost} XP]"))
                elif item_id == 9:  # Silencer: 24h protection against scaring ducks
                    now = time.time()
                    duration = 24 * 3600
                    if channel_stats.get('silencer_until', 0) > now:
                        await self.send_notice(network, user, "Silencer already active. Wait until it wears off to buy more.")
                        channel_stats['xp'] += item['cost']
                    else:
                        channel_stats['silencer_until'] = now + duration
                        await self.send_message(network, channel, self.pm(user, f"{self.colorize('You purchased a silencer.', 'green')} It will prevent frightening ducks for 24h. {self.colorize(f'[-{cost} XP]', 'red')}"))
                elif item_id == 20:  # Bread: next 20 befriends count double vs golden
                    if channel_stats.get('bread_uses', 0) > 0:
                        await self.send_notice(network, user, "Bread already active. Use it up before buying more.")
                        channel_stats['xp'] += item['cost']
                    else:
                        channel_stats['bread_uses'] = 20
                        await self.send_message(network, channel, self.pm(user, f"{self.colorize('You purchased bread.', 'green')} Next 20 befriends are more effective. {self.colorize(f'[-{cost} XP]', 'red')}"))
                elif item_id == 5:  # Repurchase confiscated gun
                    if channel_stats['confiscated']:
                        channel_stats['confiscated'] = False
                        clip_size = channel_stats.get('clip_size', 10)
                        mags_max = channel_stats.get('magazines_max', 2)
                        channel_stats['ammo'] = clip_size
                        channel_stats['magazines'] = mags_max
                        await self.send_message(network, channel, self.pm(user, f"You repurchased your confiscated gun. [-{cost} XP] | Ammo: {clip_size}/{clip_size} | Magazines: {mags_max}/{mags_max}"))
                    else:
                        await self.send_message(network, channel, f"Your gun is not confiscated.")
                        channel_stats['xp'] += item['cost']  # Refund XP
                elif item_id == 21:  # Ducks detector (shop: full 24h duration)
                    now = time.time()
                    duration = 24 * 3600
                    current_until = channel_stats.get('ducks_detector_until', 0)
                    channel_stats['ducks_detector_until'] = max(current_until, now + duration)
                    await self.send_message(network, channel, self.pm(user, f"Ducks detector activated for 24h. You'll get a 60s pre-spawn notice. [-{cost} XP]"))
                elif item_id == 23:  # Extra Magazine: increase magazines_max (level 1-5), cost scales
                    current_level = channel_stats.get('mag_capacity_level', 0)
                    if current_level >= 5:
                        await self.send_message(network, channel, self.pm(user, "You already carry the maximum extra magazines."))
                        channel_stats['xp'] += item['cost']
                    else:
                        channel_stats['mag_capacity_level'] = current_level + 1
                        channel_stats['magazines_max'] = channel_stats.get('magazines_max', 2) + 1
                        # Grant one extra empty magazine immediately
                        channel_stats['magazines'] = min(channel_stats['magazines_max'], channel_stats['magazines'] + 1)
                        await self.send_message(network, channel, self.pm(user, f"Upgrade applied. You can now carry {channel_stats['magazines_max']} magazines. [-{cost} XP]"))
                        item['cost'] = min(1000, item['cost'] + 200)
                else:
                    # For other items, just show generic message
                    await self.send_message(network, channel, self.pm(user, f"{self.colorize(f'You purchased {item['name']}.', 'green')} {self.colorize(f'[-{cost} XP]', 'red')}"))
                
                # After any shop purchase that changes XP or capacities, re-apply level bonuses and announce level changes
                self.apply_level_bonuses(channel_stats)
                if channel_stats.get('xp', 0) != prev_xp:
                    await self.check_level_change(user, channel, channel_stats, prev_xp, network)
                self.save_player_data()
                
            except ValueError:
                await self.send_notice(network, user, "Invalid item ID.")
    
    async def handle_duckstats(self, user, channel, args, network: NetworkConnection):
        """Handle !duckstats command"""
        if not self.check_authentication(user):
            return
        
        target_user = args[0] if args else user
        if target_user not in self.players:
            await self.send_notice(network, user, "I do not know any hunter with that name.")
            return
        
        player = self.players[target_user]
        channel_stats = self.get_channel_stats(target_user, channel)
        
        # Calculate total stats across all channels
        total_ducks = sum(stats['ducks_shot'] for stats in player['channel_stats'].values())
        total_golden = sum(stats['golden_ducks'] for stats in player['channel_stats'].values())
        total_shots = sum(stats['shots_fired'] for stats in player['channel_stats'].values())
        total_reaction_time = sum(stats['total_reaction_time'] for stats in player['channel_stats'].values())
        total_xp = sum(stats['xp'] for stats in player['channel_stats'].values())
        
        # Find best time across all channels
        best_times = [stats['best_time'] for stats in player['channel_stats'].values() if stats['best_time']]
        best_time = min(best_times) if best_times else None
        
        avg_reaction = total_reaction_time / max(1, total_shots)
        channel_level = min(50, (channel_stats['xp'] // 100) + 1)
        
        stats_text = f"Hunting stats for {target_user} in {channel}: "
        # Accuracy display from level table (+bread/explosive not shown here)
        acc_pct = self.get_level_properties(channel_stats['xp'])['accuracy_pct']
        clip_size = channel_stats.get('clip_size', 10)
        mags_max = channel_stats.get('magazines_max', 2)
        stats_text += f"[Weapon]  ammo: {channel_stats['ammo']}/{clip_size} | mag.: {channel_stats['magazines']}/{mags_max} | jammed: {'yes' if channel_stats['jammed'] else 'no'} | confisc.: {'yes' if channel_stats['confiscated'] else 'no'}  "
        # Compute karma: proportion of good actions vs total actions
        total_bad = channel_stats.get('misses', 0) + channel_stats.get('accidents', 0) + channel_stats.get('wild_fires', 0)
        total_good = channel_stats.get('ducks_shot', 0) + channel_stats.get('befriended_ducks', 0)
        total_actions = total_bad + total_good
        karma_pct = 100.0 if total_actions == 0 else max(0.0, min(100.0, (total_good / total_actions) * 100.0))
        stats_text += f"[Profile]  {channel_stats['xp']} xp | lvl {channel_level} | accuracy: {acc_pct}% | karma: {karma_pct:.2f}% good hunter  "
        channel_best = f"{channel_stats['best_time']:.3f}s" if channel_stats['best_time'] else "N/A"
        total_best = f"{best_time:.3f}s" if best_time else "N/A"
        channel_avg = channel_stats['total_reaction_time']/max(1,channel_stats['shots_fired'])
        
        stats_text += f"[Channel Stats]  {channel_stats['ducks_shot']} ducks (incl. {channel_stats['golden_ducks']} golden) | best time: {channel_best} | avg react: {channel_avg:.3f}s  "
        stats_text += f"[Total Stats]  {total_ducks} ducks (incl. {total_golden} golden) | {total_xp} xp | best time: {total_best} | avg react: {avg_reaction:.3f}s"

        # Show consumables/effects with remaining counts or durations
        ap = channel_stats.get('ap_shots', 0)
        ex = channel_stats.get('explosive_shots', 0)
        bread = channel_stats.get('bread_uses', 0)
        parts = []
        if ap > 0:
            ap_label = f"AP Ammo [{ap}/20]" if ap <= 20 else f"AP Ammo [{ap}]"
            parts.append(ap_label)
        if ex > 0:
            ex_label = f"Explosive Ammo [{ex}/20]" if ex <= 20 else f"Explosive Ammo [{ex}]"
            parts.append(ex_label)
        if bread > 0:
            br_label = f"Bread [{bread}/20]" if bread <= 20 else f"Bread [{bread}]"
            parts.append(br_label)
        now = time.time()
        # Helper to format remaining time
        def fmt_dur(until: float) -> str:
            rem = int(until - now)
            if rem <= 0:
                return "0m"
            if rem >= 3600:
                h = rem // 3600
                m = (rem % 3600) // 60
                return f"{h}h{m:02d}m"
            else:
                m = rem // 60
                s = rem % 60
                return f"{m}m{s:02d}s"
        # Timed effects
        if channel_stats.get('grease_until', 0) > now:
            parts.append(f"Grease [{fmt_dur(channel_stats['grease_until'])}]")
        if channel_stats.get('silencer_until', 0) > now:
            parts.append(f"Silencer [{fmt_dur(channel_stats['silencer_until'])}]")
        if channel_stats.get('sunglasses_until', 0) > now:
            parts.append(f"Sunglasses [{fmt_dur(channel_stats['sunglasses_until'])}]")
        if channel_stats.get('clover_until', 0) > now:
            bonus = int(channel_stats.get('clover_bonus', 0))
            parts.append(f"Four-leaf clover +{bonus} [{fmt_dur(channel_stats['clover_until'])}]")
        if channel_stats.get('mirror_until', 0) > now:
            parts.append(f"Mirror [{fmt_dur(channel_stats['mirror_until'])}]")
        if channel_stats.get('sand_until', 0) > now:
            parts.append(f"Sand [{fmt_dur(channel_stats['sand_until'])}]")
        if channel_stats.get('soaked_until', 0) > now:
            parts.append(f"Soaked [{fmt_dur(channel_stats['soaked_until'])}]")
        if channel_stats.get('life_insurance_until', 0) > now:
            parts.append(f"Life insurance [{fmt_dur(channel_stats['life_insurance_until'])}]")
        if channel_stats.get('liability_insurance_until', 0) > now:
            parts.append(f"Liability insurance [{fmt_dur(channel_stats['liability_insurance_until'])}]")
        if channel_stats.get('brush_until', 0) > now:
            parts.append(f"Brush [{fmt_dur(channel_stats['brush_until'])}]")
        # Ducks detector remaining time
        if channel_stats.get('ducks_detector_until', 0) > now:
            parts.append(f"Ducks Detector [{fmt_dur(channel_stats['ducks_detector_until'])}]")
        # Infrared detector remaining time and uses
        infrared_until = channel_stats.get('infrared_until', 0)
        if infrared_until and infrared_until > now:
            parts.append(f"Infrared Detector [{fmt_dur(infrared_until)}]")
            ir_uses = channel_stats.get('infrared_uses', 0)
            if ir_uses > 0:
                parts.append(f"Infrared Uses [{ir_uses}/6]")
        # Sight
        if channel_stats.get('sight_next_shot', False):
            parts.append("Sight [next shot]")
        if parts:
            stats_text += "  |  Effects: " + " | ".join(parts)
        
        await self.send_notice(network, user, stats_text)
    
    async def handle_topduck(self, user, channel, args, network: NetworkConnection):
        """Handle !topduck command"""
        if not self.check_authentication(user):
            return
        
        # Check if user wants duck count instead of XP
        if args and args[0].lower() == "duck":
            # Sort players by ducks killed in this channel
            player_channel_stats = []
            for player_name, player_data in self.players.items():
                channel_stats = self.get_channel_stats(player_name, channel)
                if channel_stats['ducks_shot'] > 0:
                    player_channel_stats.append((player_name, channel_stats['ducks_shot']))
            
            sorted_players = sorted(player_channel_stats, key=lambda x: x[1], reverse=True)
            top_players = sorted_players[:5]
            
            if not top_players:
                top_text = "The scoreboard is empty. There are no top ducks."
            else:
                top_text = "The top duck(s) in " + channel + " by ducks killed are: "
                player_list = []
                for player_name, ducks_shot in top_players:
                    player_list.append(f"{player_name} with {ducks_shot} ducks")
                top_text += " | ".join(player_list)
        else:
            # Sort players by XP in this channel (default behavior)
            player_channel_xp = []
            for player_name, player_data in self.players.items():
                channel_stats = self.get_channel_stats(player_name, channel)
                if channel_stats['xp'] > 0:
                    player_channel_xp.append((player_name, channel_stats['xp']))
            
            sorted_players = sorted(player_channel_xp, key=lambda x: x[1], reverse=True)
            top_players = sorted_players[:5]
            
            if not top_players:
                top_text = "The scoreboard is empty. There are no top ducks."
            else:
                top_text = "The top duck(s) in " + channel + " by total xp are: "
                player_list = []
                for player_name, xp in top_players:
                    player_list.append(f"{player_name} with {xp} total xp")
                top_text += " | ".join(player_list)
        
        await self.send_message(network, channel, top_text)
    
    async def handle_duckhelp(self, user, channel, network: NetworkConnection):
        """Handle !duckhelp command"""
        help_text = "Duck Hunt Commands: !bang, !bef, !reload, !shop, !duckstats, !topduck [duck], !lastduck, !duckhelp"
        await self.send_notice(network, user, help_text)
    
    async def handle_lastduck(self, user, channel, network: NetworkConnection):
        """Handle !lastduck command"""
        if not self.check_authentication(user):
            await self.send_message(network, channel, f"{user}: You must be authenticated to play.")
            return
        
        player = self.get_player(user)
        channel_stats = self.get_channel_stats(user, channel)
        
        # Check if there's currently an active duck
        norm_channel = self.normalize_channel(channel)
        if norm_channel in self.active_ducks:
            await self.send_message(network, channel, f"{user} > There is currently a duck in {channel}.")
            return
        
        if norm_channel not in self.channel_last_duck_time:
            await self.send_message(network, channel, f"{user} > No ducks have been killed in {channel} yet.")
            return
        
        current_time = time.time()
        time_diff = current_time - self.channel_last_duck_time[norm_channel]
        
        hours = int(time_diff // 3600)
        minutes = int((time_diff % 3600) // 60)
        seconds = int(time_diff % 60)
        
        time_str = ""
        if hours > 0:
            time_str += f"{hours} hour{'s' if hours != 1 else ''} "
        if minutes > 0:
            time_str += f"{minutes} minute{'s' if minutes != 1 else ''} "
        if seconds > 0 or not time_str:
            time_str += f"{seconds} second{'s' if seconds != 1 else ''}"
        
        await self.send_message(network, channel, f"{user} > The last duck was seen in {channel}: {time_str} ago.")
    
    async def handle_admin_command(self, user, channel, command, args, network: NetworkConnection):
        """Handle admin commands"""
        if not self.is_admin(user, network) and not self.is_owner(user, network):
            await self.send_notice(network, user, "You don't have permission to use admin commands.")
            return
        
        if command == "spawnduck":
            count = 1
            if args and args[0].isdigit():
                count = min(int(args[0]), self.get_network_max_ducks(network))
            
            spawned = 0
            norm_channel = self.normalize_channel(channel)
            async with self.ducks_lock:
                if norm_channel not in self.active_ducks:
                    self.active_ducks[norm_channel] = []
                remaining_capacity = max(0, self.get_network_max_ducks(network) - len(self.active_ducks[norm_channel]))
            to_spawn = min(count, remaining_capacity)
            for _ in range(to_spawn):
                # Do not push back the automatic timer when spawning manually
                await self.spawn_duck(network, channel, schedule=False)
                spawned += 1
            
            if spawned > 0:
                self.log_action(f"{user} spawned {spawned} duck(s) in {channel}.")
            else:
                await self.send_notice(network, user, f"Cannot spawn ducks in {channel} - already at maximum ({self.get_network_max_ducks(network)})")
        elif command == "spawngold":
            # Spawn a golden duck (respect per-channel capacity)
            async with self.ducks_lock:
                norm_channel = self.normalize_channel(channel)
                if norm_channel not in self.active_ducks:
                    self.active_ducks[norm_channel] = []
                if len(self.active_ducks[norm_channel]) >= self.get_network_max_ducks(network):
                    await self.send_notice(network, user, f"Cannot spawn golden duck in {channel} - already at maximum ({self.get_network_max_ducks(network)})")
                    return
                golden_duck = {'golden': True, 'health': 5, 'spawn_time': time.time(), 'revealed': False}
                self.active_ducks[norm_channel].append(golden_duck)
            # Create duck art with custom coloring: dust=gray, duck=yellow, QUACK=red/green/gold
            dust = "-.,¸¸.-·°'`'°·-.,¸¸.-·°'`'°· "
            duck = "\\_O<"
            quack = "   QUACK"
            
            # Color the parts separately
            dust_colored = self.colorize(dust, 'grey')
            duck_colored = self.colorize(duck, 'yellow')
            quack_colored = f"   {self.colorize('Q', 'red')}{self.colorize('U', 'green')}{self.colorize('A', 'yellow')}{self.colorize('C', 'red')}{self.colorize('K', 'green')}"
            
            duck_art = f"{dust_colored}{duck_colored}{quack_colored}"
            await self.send_message(network, channel, duck_art)
            self.log_action(f"{user} spawned golden duck in {channel}")
            # Do not reset per-channel timer on manual spawns
        elif command == "rearm" and args:
            target = args[0]
            if target in self.players:
                channel_stats = self.get_channel_stats(target, channel)
                channel_stats['confiscated'] = False
                clip_size = channel_stats.get('clip_size', 10)
                mags_max = channel_stats.get('magazines_max', 2)
                channel_stats['ammo'] = clip_size
                channel_stats['magazines'] = mags_max
                await self.send_message(network, channel, f"{target} has been rearmed.")
                self.save_player_data()
        elif command == "disarm" and args:
            target = args[0]
            if target in self.players:
                channel_stats = self.get_channel_stats(target, channel)
                channel_stats['confiscated'] = True
                # Optionally also empty ammo
                channel_stats['ammo'] = 0
                await self.send_message(network, channel, f"{target} has been disarmed.")
                self.save_player_data()
    
    async def handle_owner_command(self, user, command, args, network: NetworkConnection):
        """Handle owner commands via PRIVMSG"""
        self.log_action(f"handle_owner_command called: user={user}, command={command}")
        if not self.is_owner(user, network):
            self.log_action(f"User {user} is not owner")
            await self.send_notice(network, user, "You don't have permission to use owner commands.")
            return
        self.log_action(f"User {user} is owner, processing command {command}")
        
        if command == "add" and len(args) >= 2:
            if args[0] == "owner":
                # Add owner logic
                await self.send_notice(network, user, f"Added {args[1]} to owner list.")
            elif args[0] == "admin":
                # Add admin logic
                await self.send_notice(network, user, f"Added {args[1]} to admin list.")
        elif command == "disarm" and len(args) >= 2:
            target = args[0]
            channel = args[1]
            if target in self.players:
                channel_stats = self.get_channel_stats(target, channel)
                channel_stats['confiscated'] = True
                channel_stats['ammo'] = 0
                await self.send_notice(network, user, f"{target} has been disarmed in {channel}.")
                self.save_player_data()
        elif command == "reload":
            self.load_config("duckhunt.conf")
            # Note: This is a global command, so we can't send to a specific network
            # For now, just log the reload
        elif command == "restart":
            self.log_action(f"Restart command received from {user}")
            # Note: This is a global command, so we can't send to a specific network
            # For now, just log the restart
            self.log_action(f"{user} restarted the bot.")
            # Save data before restart
            self.save_player_data()
            # Close connection and exit
            # Note: This is a global command, so we can't close a specific network socket
            exit(0)
        elif command == "join" and args:
            channel = args[0]
            # Join the channel on the network where the command was received
            await self.send_network(network, f"JOIN {channel}")
            network.channels[channel] = set()
            self.log_action(f"Joined {channel} on {network.name} by {user}")
            # Schedule a duck spawn for the new channel
            await self.schedule_channel_next_duck(network, channel)
            await self.send_notice(network, user, f"Joined {channel} on {network.name}")
        elif command == "clear" and args:
            channel = args[0]
            # Note: This is a global command, so we can't check a specific network
            # For now, just log the clear request
            self.log_action(f"Clear command received for {channel} from {user}")
            
            norm_channel = self.normalize_channel(channel)
            # Clear all player data for this channel (normalize player keys)
            cleared_count = 0
            for _player_name, player_data in self.players.items():
                stats_map = player_data.get('channel_stats', {})
                to_delete = [ch for ch in list(stats_map.keys()) if self.normalize_channel(ch) == norm_channel]
                if to_delete:
                    for ch in to_delete:
                        del stats_map[ch]
                    cleared_count += 1
            
            # Clear ducks for this channel
            async with self.ducks_lock:
                if norm_channel in self.active_ducks:
                    del self.active_ducks[norm_channel]
            
            # Note: This is a global command, so we can't send to a specific network
            # For now, just log the clear completion
            self.log_action(f"{user} cleared all data for {channel}")
            self.save_player_data()
        elif command == "part" and args:
            channel = args[0]
            # Note: This is a global command, so we can't part from a specific network
            # For now, just log the part request
            self.log_action(f"Part command received for {channel} from {user}")
        elif command == "nextduck":
            # Owner-only: report next scheduled spawn for this channel
            now = time.time()
            # Match schedule key by normalized channel to avoid trailing-space mismatch
            norm = self.normalize_channel(channel)
            key = None
            for k in list(network.channel_next_spawn.keys()):
                if self.normalize_channel(k) == norm:
                    key = k
                    break
            next_time = network.channel_next_spawn.get(key) if key else None
            if not next_time:
                # No schedule exists yet - create one but don't show it as immediate
                await self.schedule_channel_next_duck(network, channel, allow_immediate=False)
                # Get the newly created schedule
                for k in list(network.channel_next_spawn.keys()):
                    if self.normalize_channel(k) == norm:
                        key = k
                        break
                next_time = network.channel_next_spawn.get(key) if key else None
                if not next_time:
                    await self.send_message(network, channel, f"{user} > No spawn scheduled yet for {channel}.")
                    return
            remaining = max(0, int(next_time - now))
            minutes = remaining // 60
            seconds = remaining % 60
            await self.send_message(network, channel, f"{user} > Next duck in {minutes}m{seconds:02d}s.")
    
    async def process_message(self, data, network: NetworkConnection):
        """Process incoming IRC message"""
        self.log_message("RECV", data.strip())
        
        # Handle PING
        if data.startswith("PING"):
            pong_response = data.replace("PING", "PONG")
            await self.send_network(network, pong_response)
            return
        
        # Handle registration complete (001 message)
        if "001" in data and "Welcome" in data:
            network.registered = True
            # Set a timeout for MOTD completion (30 seconds)
            network.motd_start_time = time.time()
            return
        
        # Handle MOTD end (376 message) - now we can complete registration
        if "376" in data and "End of /MOTD command" in data:
            await self.complete_registration(network)
            return
        
        # Count MOTD messages and force completion after too many
        if network.registered and hasattr(network, 'motd_start_time') and not hasattr(network, 'registration_complete'):
            if "372" in data or "375" in data or "376" in data:
                network.motd_message_count += 1
                if network.motd_message_count > 50:  # Force completion after 50 MOTD messages
                    self.log_action(f"MOTD message limit reached for {network.name} ({network.motd_message_count} messages) - completing registration")
                    network.motd_timeout_triggered = True
                    await self.complete_registration(network)
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
                    await self.handle_channel_message(user, target, message, network)
                else:
                    # Private message
                    self.log_message("PRIVMSG", f"{user}: {message}")
                    await self.handle_private_message(user, message, network)
        
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
                if channel in network.channels:
                    network.channels[channel].add(user)
                self.log_message("JOIN", f"{user} joined {channel}")
                # If we (the bot) joined, ensure a schedule is created
                try:
                    if user == network.nick:
                        await self.schedule_channel_next_duck(network, channel)
                except Exception as e:
                    self.log_action(f"Failed to schedule on self JOIN for {channel}: {e}")
        
        elif "PART" in data:
            # User left channel
            match = re.search(r':([^!]+)![^@]+@[^ ]+ PART (.+)', data)
            if match:
                user = match.group(1)
                channel = match.group(2).lstrip(':')
                if channel in network.channels:
                    network.channels[channel].discard(user)
                self.log_message("PART", f"{user} left {channel}")
        
        elif "QUIT" in data:
            # User quit
            match = re.search(r':([^!]+)![^@]+@[^ ]+ QUIT', data)
            if match:
                user = match.group(1)
                # Remove from all channels
                for channel in network.channels:
                    network.channels[channel].discard(user)
                self.log_message("QUIT", f"{user} quit")
        
        else:
            # Server message
            self.log_message("SERVER", data.strip())
    
    async def handle_channel_message(self, user, channel, message, network: NetworkConnection):
        """Handle channel message"""
        if not message.startswith('!'):
            return
        
        command_parts = message[1:].split()
        command = command_parts[0].lower() if command_parts else ""
        
        # Ensure channel has a schedule; if missing, create one lazily (but do not force immediate)
        try:
            if command == 'nextduck':
                pass  # don't create schedule here; handled below without immediate spawn
            else:
                if not network.channel_next_spawn.get(channel):
                    await self.schedule_channel_next_duck(network, channel)
        except Exception as e:
            self.log_action(f"Lazy schedule init failed for {channel}: {e}")

        args = command_parts[1:] if len(command_parts) > 1 else []
        
        self.log_action(f"Detected {command} from {user} in {channel}")
        # Command aliases / typos
        if command in ["spawduck", "spawn", "sd"]:
            command = "spawnduck"
        elif command in ["spawng", "sg"]:
            command = "spawngold"
        
        if command == "bang":
            await self.handle_bang(user, channel, network)
        elif command == "bef":
            await self.handle_bef(user, channel, network)
        elif command == "reload":
            await self.handle_reload(user, channel, network)
        elif command == "shop":
            await self.handle_shop(user, channel, args, network)
        elif command == "duckstats":
            await self.handle_duckstats(user, channel, args, network)
        elif command == "topduck":
            await self.handle_topduck(user, channel, args, network)
        elif command == "lastduck":
            await self.handle_lastduck(user, channel, network)
        elif command == "duckhelp":
            await self.handle_duckhelp(user, channel, network)
        elif command == "nextduck":
            # Owner-only, invoked in channel
            if not self.is_owner(user, network):
                return
            now = time.time()
            norm = self.normalize_channel(channel)
            key = None
            for k in list(network.channel_next_spawn.keys()):
                if self.normalize_channel(k) == norm:
                    key = k
                    break
            next_time = network.channel_next_spawn.get(key) if key else None
            if not next_time:
                # Only schedule if no schedule exists at all
                await self.schedule_channel_next_duck(network, channel, allow_immediate=False)
                # Get the newly created schedule using the same key lookup
                for k in list(network.channel_next_spawn.keys()):
                    if self.normalize_channel(k) == norm:
                        key = k
                        break
                next_time = network.channel_next_spawn.get(key) if key else None
                if not next_time:
                    await self.send_message(network, channel, f"{user} > No spawn scheduled yet for {channel}.")
                    return
            remaining = max(0, int(next_time - now))
            minutes = remaining // 60
            seconds = remaining % 60
            await self.send_message(network, channel, f"{user} > Next duck in {minutes}m{seconds:02d}s.")
        elif command in ["spawnduck", "spawngold", "rearm", "disarm"]:
            await self.handle_admin_command(user, channel, command, args, network)

    # --- Loot System ---
    async def apply_weighted_loot(self, user: str, channel: str, channel_stats: dict, network: NetworkConnection) -> None:
        """Weighted random loot based on historical drop rates. Applies effects and announces."""
        # Define loot weights (sum does not need to be 1)
        loot = [
            ("extra_bullet", 18.4),
            ("sight_next", 13.0),
            ("silencer", 12.4),
            ("ducks_detector", 11.9),
            ("extra_mag", 11.1),
            ("ap_ammo", 7.8),
            ("grease", 7.2),
            ("sunglasses", 7.0),
            ("explosive_ammo", 6.0),
            ("infrared", 4.4),
            ("wallet_150xp", 0.5),
            ("hunting_mag", 3.0),  # covers 10/20/40/50/100 xp random
            ("clover", 3.2),       # covers +1,+3,+5,+7,+8,+9,+10 XP/duck
            ("junk", 15.0),
        ]
        total = sum(w for _, w in loot)
        roll = random.uniform(0, total)
        acc = 0.0
        choice = loot[-1][0]
        for name, weight in loot:
            acc += weight
            if roll <= acc:
                choice = name
                break

        # Apply effect
        now = time.time()
        day = 24 * 3600
        clip_size = channel_stats.get('clip_size', 10)
        mags_max = channel_stats.get('magazines_max', 2)

        async def say(msg: str) -> None:
            await self.send_message(network, channel, self.pm(user, msg))

        if choice == "extra_bullet":
            if channel_stats['ammo'] < clip_size:
                channel_stats['ammo'] = min(clip_size, channel_stats['ammo'] + 1)
                await say(f"By searching the bushes, you find an extra bullet! | Ammo: {channel_stats['ammo']}/{clip_size}")
            else:
                xp = 7
                channel_stats['xp'] += xp
                await say(f"By searching the bushes, you find an extra bullet! Your magazine is full, so you gain {xp} XP instead.")
        elif choice == "extra_mag":
            if channel_stats['magazines'] < mags_max:
                channel_stats['magazines'] = min(mags_max, channel_stats['magazines'] + 1)
                await say(f"By searching the bushes, you find an extra ammo clip! | Magazines: {channel_stats['magazines']}/{mags_max}")
            else:
                xp = 20
                channel_stats['xp'] += xp
                await say(f"By searching the bushes, you find an extra ammo clip! You already have maximum magazines, so you gain {xp} XP instead.")
        elif choice == "sight_next":
            # If already active, convert to XP equal to shop price (shop_sight)
            if channel_stats.get('sight_next_shot', False):
                sight_cost = int(self.config.get('DEFAULT', 'shop_sight', fallback=6))
                channel_stats['xp'] += sight_cost
                await say(f"You find a sight, but you already have one mounted for your next shot. [+{sight_cost} xp]")
            else:
                channel_stats['sight_next_shot'] = True
                await say("By searching the bushes, you find a sight for your gun! Your next shot will be more accurate.")
        elif choice == "silencer":
            if channel_stats.get('silencer_until', 0) > now:
                cost = int(self.config.get('DEFAULT', 'shop_silencer', fallback=5))
                channel_stats['xp'] += cost
                await say(f"You find a silencer, but you already have one active. [+{cost} xp]")
            else:
                channel_stats['silencer_until'] = now + day
                await say("By searching the bushes, you find a silencer! It will prevent frightening ducks for 24h.")
        elif choice == "ducks_detector":
            if channel_stats.get('ducks_detector_until', 0) > now:
                cost = int(self.config.get('DEFAULT', 'shop_ducks_detector', fallback=50))
                channel_stats['xp'] += cost
                await say(f"You find a ducks detector, but you already have one active. [+{cost} xp]")
            else:
                channel_stats['ducks_detector_until'] = now + day
                await say("By searching the bushes, you find a ducks detector! You'll get a 60s pre-spawn notice for 24h.")
        elif choice == "ap_ammo":
            if channel_stats.get('ap_shots', 0) > 0:
                xp = int(self.config.get('DEFAULT', 'shop_ap_ammo', fallback=15))
                channel_stats['xp'] += xp
                await say(f"You find AP ammo, but you already have some. [+{xp} xp]")
            else:
                channel_stats['explosive_shots'] = 0
                channel_stats['ap_shots'] = 20
                await say("By searching the bushes, you find AP ammo! Next 20 shots deal extra damage to golden ducks.")
        elif choice == "explosive_ammo":
            if channel_stats.get('explosive_shots', 0) > 0:
                xp = int(self.config.get('DEFAULT', 'shop_explosive_ammo', fallback=25))
                channel_stats['xp'] += xp
                await say(f"You find explosive ammo, but you already have some. [+{xp} xp]")
            else:
                channel_stats['ap_shots'] = 0
                channel_stats['explosive_shots'] = 20
                await say("By searching the bushes, you find explosive ammo! Next 20 shots deal extra damage to golden ducks.")
        elif choice == "grease":
            if channel_stats.get('grease_until', 0) > now:
                cost = int(self.config.get('DEFAULT', 'shop_grease', fallback=8))
                channel_stats['xp'] += cost
                await say(f"You find grease, but you already have some applied. [+{cost} xp]")
            else:
                channel_stats['grease_until'] = now + day
                await say("By searching the bushes, you find grease! Your gun will jam half as often for 24h.")
        elif choice == "sunglasses":
            if channel_stats.get('sunglasses_until', 0) > now:
                cost = int(self.config.get('DEFAULT', 'shop_sunglasses', fallback=5))
                channel_stats['xp'] += cost
                await say(f"You find sunglasses, but you're already wearing some. [+{cost} xp]")
            else:
                channel_stats['sunglasses_until'] = now + day
                await say("By searching the bushes, you find sunglasses! You're protected against bedazzlement for 24h.")
        elif choice == "infrared":
            if channel_stats.get('infrared_until', 0) > now and channel_stats.get('infrared_uses', 0) > 0:
                cost = int(self.config.get('DEFAULT', 'shop_infrared_detector', fallback=15))
                channel_stats['xp'] += cost
                await say(f"You find an infrared detector, but yours is still active. [+{cost} xp]")
            else:
                channel_stats['infrared_until'] = now + day
                channel_stats['infrared_uses'] = max(channel_stats.get('infrared_uses', 0), 6)
                await say("By searching the bushes, you find an infrared detector! Trigger locks when no duck (6 uses, 24h).")
        elif choice == "wallet_150xp":
            xp = 150
            channel_stats['xp'] += xp
            # Try to pick a random victim name from channel
            victim = None
            if channel in network.channels and network.channels[channel]:
                victim = random.choice(list(network.channels[channel]))
            owner_text = f" {victim}'s" if victim else " a"
            await say(f"By searching the bushes, you find{owner_text} lost wallet! [+{xp} xp]")
        elif choice == "hunting_mag":
            if channel_stats['magazines'] >= mags_max:
                xp_options = [10, 20, 40, 50, 100]
                xp = random.choice(xp_options)
                channel_stats['xp'] += xp
                await say(f"By searching the bushes, you find a hunting magazine! You already have maximum magazines, so you gain {xp} XP instead.")
            else:
                channel_stats['magazines'] = min(mags_max, channel_stats['magazines'] + 1)
                await say(f"By searching the bushes, you find a hunting magazine! | Magazines: {channel_stats['magazines']}/{mags_max}")
        elif choice == "clover":
            # If already active, convert to XP equal to shop price
            if channel_stats.get('clover_until', 0) > now:
                clover_cost = int(self.config.get('DEFAULT', 'shop_four_leaf_clover', fallback=13))
                channel_stats['xp'] += clover_cost
                await say(f"You find a four-leaf clover, but you already have its luck active. [+{clover_cost} xp]")
            else:
                options = [1, 3, 5, 7, 8, 9, 10]
                bonus = random.choice(options)
                channel_stats['clover_bonus'] = bonus
                channel_stats['clover_until'] = max(channel_stats.get('clover_until', 0), now + day)
                await say(f"By searching the bushes, you find a four-leaf clover! +{bonus} XP per duck for 24h.")
        else:  # junk
            junk_items = [
                "discarded tire", "old shoe", "creepy crawly", "pile of rubbish", "cigarette butt",
                "broken compass", "expired hunting license", "rusty can", "tangled fishing line",
            ]
            junk = random.choice(junk_items)
            await say(f"By searching the bushes, you find a {junk}. It's worthless.")

        self.save_player_data()
    
    async def handle_private_message(self, user, message, network: NetworkConnection):
        """Handle private message"""
        self.log_action(f"Private message from {user}: {message}")
        command_parts = message.split()
        if not command_parts:
            return
        
        command = command_parts[0].lower()
        # Remove ! prefix if present
        if command.startswith('!'):
            command = command[1:]
        
        args = command_parts[1:] if len(command_parts) > 1 else []
        
        self.log_action(f"Private command: {command}, args: {args}")
        
        if command in ["add", "reload", "restart", "join", "part", "clear"]:
            self.log_action(f"Calling handle_owner_command for {command}")
            await self.handle_owner_command(user, command, args, network)
    
    async def run(self):
        """Main bot loop"""
        # Connect to all networks
        tasks = []
        for network_name, network in self.networks.items():
            task = asyncio.create_task(self.run_network(network))
            tasks.append(task)
        
        # Run all networks concurrently
        await asyncio.gather(*tasks)
    
    async def run_network(self, network: NetworkConnection):
        """Run a single network connection"""
        await self.connect_network(network)
        
        while True:
            try:
                data = await asyncio.get_event_loop().sock_recv(network.sock, 1024)
                if data:
                    # Process each line
                    for line in data.decode('utf-8').split('\r\n'):
                        if line.strip():
                            await self.process_message(line, network)
                            network.message_count += 1
                
                # Check for MOTD timeout (30 seconds) or message limit (100 messages)
                if network.registered and hasattr(network, 'motd_start_time') and not hasattr(network, 'registration_complete') and not network.motd_timeout_triggered:
                    elapsed = time.time() - network.motd_start_time
                    if elapsed > 30 or network.message_count > 100:
                        self.log_action(f"MOTD timeout for {network.name} ({elapsed:.1f}s, {network.message_count} messages) - completing registration")
                        network.motd_timeout_triggered = True
                        await self.complete_registration(network)
                    elif elapsed > 25:  # Debug logging
                        self.log_action(f"MOTD timeout approaching for {network.name}: {elapsed:.1f}s elapsed ({network.message_count} messages)")
                
                # Per-channel pre-spawn notices and spawns (only after registration)
                if hasattr(network, 'registration_complete'):
                    # Send any due pre-notices
                    await self.notify_duck_detector(network)
                    # Perform any due spawns per channel
                    now = time.time()
                    for ch, when in list(network.channel_next_spawn.items()):
                        if when and now >= when:
                            # If channel can't accept a new duck yet, defer by 5-15s
                            if not await self.can_spawn_duck(ch, network):
                                network.channel_next_spawn[ch] = now + random.randint(5, 15)
                                continue
                            await self.spawn_duck(network, ch)
                            # Clear consumed schedule entry to avoid double triggers
                            network.channel_next_spawn[ch] = None
                
                # Duck despawn is handled in the exception handler with proper throttling
                
            except socket.error as e:
                if e.errno == 11:  # EAGAIN/EWOULDBLOCK - no data available
                    # Check for MOTD timeout (30 seconds)
                    if network.registered and hasattr(network, 'motd_start_time') and not hasattr(network, 'registration_complete') and not network.motd_timeout_triggered:
                        elapsed = time.time() - network.motd_start_time
                        if elapsed > 30:
                            self.log_action(f"MOTD timeout for {network.name} ({elapsed:.1f}s) - completing registration")
                            network.motd_timeout_triggered = True
                            await self.complete_registration(network)
                        elif elapsed > 25:  # Debug logging
                            self.log_action(f"MOTD timeout approaching for {network.name} (no data): {elapsed:.1f}s elapsed")
                    
                    # Per-channel pre-spawn notices and spawns during idle
                    if hasattr(network, 'registration_complete'):
                        await self.notify_duck_detector(network)
                        now = time.time()
                        for ch, when in list(network.channel_next_spawn.items()):
                            if when and now >= when:
                                if not await self.can_spawn_duck(ch, network):
                                    network.channel_next_spawn[ch] = now + random.randint(5, 15)
                                    continue
                                await self.spawn_duck(network, ch)
                                network.channel_next_spawn[ch] = None
                    
                    # Check for duck despawn (only after registration, throttled to once per second)
                    if hasattr(network, 'registration_complete'):
                        current_time = time.time()
                        if current_time - network.last_despawn_check >= 1.0:
                            await self.despawn_old_ducks(network)
                            network.last_despawn_check = current_time
                    
                    await asyncio.sleep(0.1)  # Small delay to prevent busy waiting
                    continue
                else:
                    self.log_action(f"Socket error: {e}")
                    break
            except Exception as e:
                self.log_action(f"Error: {e}")
                break
        
        network.sock.close()

if __name__ == "__main__":
    bot = DuckHuntBot()
    asyncio.run(bot.run())
