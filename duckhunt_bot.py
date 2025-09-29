#!/usr/bin/env python3
"""
Duck Hunt IRC Bot v1.0
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
        self.channel_ducks = {}  # Per-channel duck lists: {channel: [{'spawn_time': time, 'golden': bool}]}
        self.active_ducks = {}  # Per-channel duck lists: {channel: [ {'spawn_time': time, 'golden': bool, 'health': int}, ... ]}
        self.duck_spawn_time = None
        self.version = "1.0_build36"
        self.registered = False
        self.motd_timeout_triggered = False
        self.message_count = 0
        self.motd_message_count = 0
        self.last_despawn_check = 0
        self.ducks_lock = threading.Lock()
        # Next spawn pre-notice tracking
        self.next_spawn_channel = None
        self.pre_spawn_notice_time = None
        self.next_spawn_notice_sent = False
        
        # Game settings
        self.min_spawn = int(self.config.get('min_spawn', 600))
        self.max_spawn = int(self.config.get('max_spawn', 1800))
        self.gold_ratio = float(self.config.get('gold_ratio', 0.1))
        self.max_ducks = int(self.config.get('max_ducks', 5))
        self.despawn_time = int(self.config.get('despawn_time', 720))  # 12 minutes default
        
        # Shop items (prices loaded from config)
        self.shop_items = {
            1: {"name": "Extra bullet", "cost": int(self.config.get('shop_extra_bullet', 7)), "description": "Adds one bullet to your gun"},
            2: {"name": "Refill magazine", "cost": int(self.config.get('shop_extra_magazine', 20)), "description": "Adds one spare magazine to your stock"},
            3: {"name": "AP ammo", "cost": int(self.config.get('shop_ap_ammo', 15)), "description": "Armor-piercing ammunition"},
            4: {"name": "Explosive ammo", "cost": int(self.config.get('shop_explosive_ammo', 25)), "description": "Explosive ammunition (damage x3)"},
            5: {"name": "Repurchase confiscated gun", "cost": int(self.config.get('shop_repurchase_gun', 40)), "description": "Buy back your confiscated weapon"},
            6: {"name": "Grease", "cost": int(self.config.get('shop_grease', 8)), "description": "Halves jamming odds for 24h"},
            7: {"name": "Sight", "cost": int(self.config.get('shop_sight', 6)), "description": "Increases accuracy for next shot"},
            8: {"name": "Infrared detector", "cost": int(self.config.get('shop_infrared_detector', 15)), "description": "Locks trigger when no duck present"},
            9: {"name": "Silencer", "cost": int(self.config.get('shop_silencer', 5)), "description": "Prevents scaring ducks when shooting"},
            10: {"name": "Four-leaf clover", "cost": int(self.config.get('shop_four_leaf_clover', 13)), "description": "Extra XP for each duck shot"},
            11: {"name": "Sunglasses", "cost": int(self.config.get('shop_sunglasses', 5)), "description": "Protects against mirror dazzle"},
            12: {"name": "Spare clothes", "cost": int(self.config.get('shop_spare_clothes', 7)), "description": "Dry clothes after being soaked"},
            13: {"name": "Brush for gun", "cost": int(self.config.get('shop_brush_for_gun', 7)), "description": "Restores weapon condition"},
            14: {"name": "Mirror", "cost": int(self.config.get('shop_mirror', 7)), "description": "Dazzles target, reducing accuracy"},
            15: {"name": "Handful of sand", "cost": int(self.config.get('shop_handful_of_sand', 7)), "description": "Reduces target's gun reliability"},
            16: {"name": "Water bucket", "cost": int(self.config.get('shop_water_bucket', 10)), "description": "Soaks target, prevents hunting for 1h"},
            17: {"name": "Sabotage", "cost": int(self.config.get('shop_sabotage', 14)), "description": "Jams target's gun"},
            18: {"name": "Life insurance", "cost": int(self.config.get('shop_life_insurance', 10)), "description": "Protects against accidents"},
            19: {"name": "Liability insurance", "cost": int(self.config.get('shop_liability_insurance', 5)), "description": "Reduces accident penalties"},
            20: {"name": "Piece of bread", "cost": int(self.config.get('shop_piece_of_bread', 50)), "description": "Lures ducks"},
            21: {"name": "Ducks detector", "cost": int(self.config.get('shop_ducks_detector', 50)), "description": "Warns of next duck spawn"},
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
channel = #yourchannel,#anotherchannel

# Commands to perform on connect (semicolon separated)
perform = PRIVMSG YourNick :I am here

# Bot permissions
owner = YourNick
admin = Admin1,Admin2

# Game settings
min_spawn = 600
max_spawn = 1800
gold_ratio = 0.1
default_xp = 10
max_ducks = 5
despawn_time = 700

# Shop item prices (XP cost)
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

    def pm(self, user: str, message: str) -> str:
        """Prefix a message with the player's name as per UX convention."""
        return f"{user} - {message}"
    
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
        # Set socket to non-blocking mode
        self.sock.setblocking(False)
        
        # Send IRC handshake
        bot_nicks = self.config['bot_nick'].split(',')
        self.send(f"USER DuckHuntBot 0 * :Duck Hunt Game Bot v{self.version}")
        self.send(f"NICK {bot_nicks[0]}")
    
    def complete_registration(self):
        """Complete IRC registration by joining channels and running perform commands"""
        if hasattr(self, 'registration_complete'):
            return
        
        self.registration_complete = True
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

    def check_level_change(self, user: str, channel: str, stats: dict, prev_xp: int) -> None:
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
            self.send_message(channel, self.pm(user, f"PROMOTION     You are promoted to level {new_level} ({title})."))
        else:
            self.send_message(channel, self.pm(user, f"DEMOTION     You are demoted to level {new_level} ({title})."))
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
    
    def spawn_duck(self, channel=None):
        """Spawn a new duck in a specific channel"""
        if channel is None:
            # Pick a random channel
            channels = [ch.strip() for ch in self.config.get('channel', '#default').split(',') if ch.strip()]
            if not channels:
                return
            channel = random.choice(channels)
        
        with self.ducks_lock:
            norm_channel = self.normalize_channel(channel)
            if norm_channel not in self.active_ducks:
                self.active_ducks[norm_channel] = []
            # Enforce max_ducks from config
            if len(self.active_ducks[norm_channel]) >= self.max_ducks:
                return
            is_golden = random.random() < self.gold_ratio
            duck = {
                'golden': is_golden,
                'health': 5 if is_golden else 1,
                'spawn_time': time.time()
            }
            # Append new duck (FIFO)
            self.active_ducks[norm_channel].append(duck)
            # self.send_message(channel, f"[DEBUG] Duck added to active_ducks[{norm_channel}] - spawn_time: {duck['spawn_time']}")
            self.log_action(f"[DEBUG] Duck added to active_ducks[{norm_channel}] - spawn_time: {duck['spawn_time']}")
        
        # Debug logging
        self.log_action(f"Spawned {'golden' if is_golden else 'regular'} duck in {channel} - spawn_time: {duck['spawn_time']}")
        
        duck_art = "-.,¸¸.-·°'`'°·-.,¸¸.-·°'`'°· \\_O<   QUACK"
        if is_golden:
            duck_art += "   * GOLDEN DUCK DETECTED *"
        
        self.send_message(channel, duck_art)
        
        # Check active_ducks state after sending messages
        with self.ducks_lock:
            # self.send_message(channel, f"[DEBUG] Duck stored in {channel} - spawn_time: {duck['spawn_time']}")
            self.log_action(f"Duck spawned in {channel} - spawn_time: {duck['spawn_time']}")
            self.log_action(f"[DEBUG] Active_ducks state after spawn: { {ch: len(lst) for ch,lst in self.active_ducks.items()} }")
        
        # Schedule next random spawn
        self.schedule_next_duck()
    
    def schedule_next_duck(self):
        """Schedule next duck spawn"""
        spawn_delay = random.randint(self.min_spawn, self.max_spawn)
        now = time.time()
        self.duck_spawn_time = now + spawn_delay
        # Choose the channel now so we can pre-notify
        # Prefer currently joined channels; fallback to configured list
        joined_channels = list(self.channels.keys()) if getattr(self, 'channels', None) else []
        if joined_channels:
            channels = joined_channels
        else:
            channels = [ch.strip() for ch in self.config.get('channel', '#default').split(',') if ch.strip()]
        self.next_spawn_channel = random.choice(channels) if channels else None
        # 60s head start pre-notice
        self.pre_spawn_notice_time = max(now, self.duck_spawn_time - 60)
        self.next_spawn_notice_sent = False
        self.log_action(f"Next duck scheduled in {spawn_delay} seconds for {self.next_spawn_channel}")

    def notify_duck_detector(self):
        """Notify players with an active duck detector 60s before spawn."""
        if not self.next_spawn_channel:
            return
        channel = self.next_spawn_channel
        if channel not in self.channels:
            return
        now = time.time()
        # Notify each user in the channel with active detector
        for user in list(self.channels.get(channel, [])):
            try:
                stats = self.get_channel_stats(user, channel)
            except Exception:
                continue
            until = stats.get('ducks_detector_until', 0)
            if until and until > now:
                seconds_left = int(self.duck_spawn_time - now) if self.duck_spawn_time else 60
                seconds_left = max(0, seconds_left)
                minutes = seconds_left // 60
                secs = seconds_left % 60
                msg = f"[Duck Detector] A duck will spawn in {minutes}m{secs:02d}s in {channel}."
                self.send_notice(user, msg)
    
    def despawn_old_ducks(self):
        """Remove ducks that have been alive too long"""
        current_time = time.time()
        total_removed = 0
        
        # self.log_action(f"[DEBUG] despawn_old_ducks called at {current_time}")
        
        with self.ducks_lock:
            # Debug: log despawn check (throttled to avoid flooding)
            if self.active_ducks:
                pass  # reduced debug noise
            
            # Check each channel's single active duck
            for norm_channel, ducks in list(self.active_ducks.items()):
                # Filter ducks that are still within lifespan
                remaining_ducks = []
                for duck in ducks:
                    age = current_time - duck['spawn_time']
                    if age < self.despawn_time:
                        remaining_ducks.append(duck)
                    else:
                        total_removed += 1
                        # Announce quiet despawn to the channel (legacy styling)
                        self.send_message(norm_channel, "The duck flies away.     ·°'`'°-.,¸¸.·°'`")
                        # Quietly unconfiscate all on this channel when a duck despawns
                        self.unconfiscate_confiscated_in_channel(norm_channel)
                if remaining_ducks:
                    self.active_ducks[norm_channel] = remaining_ducks
                else:
                    del self.active_ducks[norm_channel]
    
    def handle_bang(self, user, channel):
        """Handle !bang command"""
        if not self.check_authentication(user):
            self.send_message(channel, self.pm(user, "You must be authenticated to play."))
            return
        
        player = self.get_player(user)
        channel_stats = self.get_channel_stats(user, channel)
        
        if channel_stats['confiscated']:
            # self.send_message(channel, f"[DEBUG] Early return: confiscated=True")
            self.send_message(channel, self.pm(user, "You are not armed."))
            return
        
        if channel_stats['jammed']:
            # self.send_message(channel, f"[DEBUG] Early return: jammed=True")
            clip_size = channel_stats.get('clip_size', 10)
            mags_max = channel_stats.get('magazines_max', 2)
            self.send_message(channel, self.pm(user, f"*CLACK*     Your gun is jammed, you must reload to unjam it... | Ammo: {channel_stats['ammo']}/{clip_size} | Magazines : {channel_stats['magazines']}/{mags_max}"))
            return
        
        if channel_stats['ammo'] <= 0:
            # self.send_message(channel, f"[DEBUG] Early return: ammo={channel_stats['ammo']}")
            clip_size = channel_stats.get('clip_size', 10)
            mags_max = channel_stats.get('magazines_max', 2)
            self.send_message(channel, self.pm(user, f"*CLICK*     EMPTY MAGAZINE | Ammo: 0/{clip_size} | Magazines: {channel_stats['magazines']}/{mags_max}"))
            return
        
        # Check if there is a duck in this channel
        with self.ducks_lock:
            norm_channel = self.normalize_channel(channel)
            # self.send_message(channel, f"[DEBUG] Bang check - all channels: {list(self.active_ducks.keys())}")
            # self.send_message(channel, f"[DEBUG] Bang check - channel in ducks: {norm_channel in self.active_ducks}")
            if norm_channel not in self.active_ducks:
                # Infrared Detector: if active AND has uses, allow safe trigger lock and consume one use
                now = time.time()
                if channel_stats.get('infrared_until', 0) > now and channel_stats.get('infrared_uses', 0) > 0:
                    channel_stats['infrared_uses'] = max(0, channel_stats.get('infrared_uses', 0) - 1)
                    remaining_uses = channel_stats.get('infrared_uses', 0)
                    self.send_message(channel, self.pm(user, f"*CLICK*     Trigger locked. [{remaining_uses} remaining]"))
                    self.save_player_data()
                    return
                # Otherwise apply classic-aligned penalties with liability reduction
                miss_pen = channel_stats.get('miss_penalty', -1)
                wild_pen = -2
                if channel_stats.get('liability_insurance_until', 0) > now:
                    if miss_pen < 0:
                        miss_pen = int(miss_pen / 2)
                    if wild_pen < 0:
                        wild_pen = int(wild_pen / 2)
                total_pen = miss_pen + wild_pen
                channel_stats['confiscated'] = True
                prev_xp = channel_stats['xp']
                channel_stats['xp'] = max(0, channel_stats['xp'] + total_pen)
                self.send_message(channel, self.pm(user, f"Luckily you missed, but what did you aim at ? There is no duck in the area...   [missed: {miss_pen} xp] [wild fire: {wild_pen} xp]   [GUN CONFISCATED: wild fire]"))
                # Accidental shooting (wild fire): 50% chance to hit a random player
                victim = None
                if channel in self.channels and self.channels[channel]:
                    candidates = [u for u in list(self.channels[channel]) if u != user]
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
                        acc_pen = int(acc_pen / 2)
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
                            extra = int(extra / 2)
                        channel_stats['xp'] = max(0, channel_stats['xp'] + extra)
                        self.send_message(channel, self.pm(user, f"ACCIDENT     You accidentally shot {victim}! [accident: {acc_pen} xp] [mirror glare: {extra} xp]{' [INSURED: no confiscation]' if insured else ''}"))
                    else:
                        self.send_message(channel, self.pm(user, f"ACCIDENT     You accidentally shot {victim}! [accident: {acc_pen} xp]{' [INSURED: no confiscation]' if insured else ''}"))
                self.check_level_change(user, channel, channel_stats, prev_xp)
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
                self.send_message(channel, self.pm(user, f"*CLACK*     Your gun is jammed, you must reload to unjam it... | Ammo: {channel_stats['ammo']}/{clip_size} | Magazines : {channel_stats['magazines']}/{mags_max}"))
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
                self.send_message(channel, self.pm(user, "You are soaked and cannot shoot. Use spare clothes or wait."))
                return
            if hit_roll > hit_chance:
                channel_stats['shots_fired'] += 1
                channel_stats['misses'] += 1
                penalty = channel_stats.get('miss_penalty', -1)
                # Liability insurance halves penalties
                if channel_stats.get('liability_insurance_until', 0) > time.time() and penalty < 0:
                    penalty = int(penalty / 2)
                prev_xp = channel_stats['xp']
                channel_stats['xp'] = max(0, channel_stats['xp'] + penalty)
                self.send_message(channel, self.pm(user, f"*BANG*     You missed. [{penalty} xp]"))
                # Ricochet accident: 20% chance to hit a random player
                victim = None
                if channel in self.channels and self.channels[channel]:
                    candidates = [u for u in list(self.channels[channel]) if u != user]
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
                        acc_pen = int(acc_pen / 2)
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
                            extra = int(extra / 2)
                        channel_stats['xp'] = max(0, channel_stats['xp'] + extra)
                        self.send_message(channel, self.pm(user, f"ACCIDENT     Your bullet ricochets into {victim}! [accident: {acc_pen} xp] [mirror glare: {extra} xp]{' [INSURED: no confiscation]' if insured else ' [GUN CONFISCATED: accident]'}"))
                    else:
                        self.send_message(channel, self.pm(user, f"ACCIDENT     Your bullet ricochets into {victim}! [accident: {acc_pen} xp]{' [INSURED: no confiscation]' if insured else ' [GUN CONFISCATED: accident]'}"))
                self.check_level_change(user, channel, channel_stats, prev_xp)
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
                # Base XP for kill (golden vs regular)
                if target_duck['golden']:
                    channel_stats['golden_ducks'] += 1
                    base_xp = 50
                else:
                    base_xp = int(self.config.get('default_xp', 10))

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
            self.send_message(channel, self.pm(user, f"*BANG*     You shot down the duck in {reaction_time:.3f}s, which makes you a total of {channel_stats['ducks_shot']} ducks on {channel}. You are promoted to level {new_level} ({title}).     \\_X<   *KWAK*   [{xp_gain} xp]{item_display}"))
        else:
            if duck_killed:
                sign = '+' if xp_gain > 0 else ''
                self.send_message(channel, self.pm(user, f"*BANG*     You shot down the duck in {reaction_time:.3f}s, which makes you a total of {channel_stats['ducks_shot']} ducks on {channel}.     \\_X<   *KWAK*   [{sign}{xp_gain} xp]{item_display}"))
            else:
                remaining = max(0, target_duck['health'])
                if target_duck['golden']:
                    self.send_message(channel, self.pm(user, f"*BANG*     The golden duck survived ! Try again.   \\_O<  [life -{damage}]"))
                else:
                    self.send_message(channel, self.pm(user, f"*BANG*     You hit the duck! Remaining health: {remaining}."))
        # Announce promotion/demotion if level changed (any XP change path)
        if xp_gain != 0:
            self.check_level_change(user, channel, channel_stats, prev_xp)
        
        # Random weighted loot drop (10% chance) on kill only
        if duck_killed and random.random() < 0.10:
            self.apply_weighted_loot(user, channel, channel_stats)
        
        self.save_player_data()
        self.schedule_next_duck()
    
    def handle_bef(self, user, channel):
        """Handle !bef (befriend) command"""
        if not self.check_authentication(user):
            self.send_message(channel, self.pm(user, "You must be authenticated to play."))
            return
        
        player = self.get_player(user)
        channel_stats = self.get_channel_stats(user, channel)
        
        # Check if there is a duck in this channel
        with self.ducks_lock:
            norm_channel = self.normalize_channel(channel)
            # self.send_message(channel, f"[DEBUG] Bef check - all channels: {list(self.active_ducks.keys())}")
            # self.send_message(channel, f"[DEBUG] Bef check - channel in ducks: {norm_channel in self.active_ducks}")
            if norm_channel not in self.active_ducks:
                self.log_action(f"No ducks to befriend in {channel} - active_ducks keys: {list(self.active_ducks.keys())}")
                # Apply small penalty for befriending when no ducks are present
                penalty = channel_stats.get('miss_penalty', -1)
                if channel_stats.get('liability_insurance_until', 0) > time.time() and penalty < 0:
                    penalty = int(penalty / 2)
                channel_stats['xp'] = max(0, channel_stats['xp'] + penalty)
                self.send_message(channel, self.pm(user, f"There are no ducks to befriend. [{penalty} XP]"))
                self.save_player_data()
                return
            
            # Get the active duck
            duck = self.active_ducks[norm_channel][0]
            
            # Accuracy-style check for befriending (duck might not notice)
            bef_roll = random.random()
            bef_chance = self.compute_accuracy(channel_stats, 'bef')
            if channel_stats.get('soaked_until', 0) > time.time():
                self.send_message(channel, self.pm(user, "You are soaked and cannot befriend. Use spare clothes or wait."))
                return
            if bef_roll > bef_chance:
                penalty = channel_stats.get('miss_penalty', -1)
                if channel_stats.get('liability_insurance_until', 0) > time.time() and penalty < 0:
                    penalty = int(penalty / 2)
                channel_stats['xp'] = max(0, channel_stats['xp'] + penalty)
                self.send_message(channel, self.pm(user, f"FRIEND     The duck seems distracted. Try again. [{penalty} XP]"))
                self.save_player_data()
                return

            # Compute befriend effectiveness
            bef_damage = 1
            if duck['golden'] and channel_stats.get('bread_uses', 0) > 0:
                bef_damage = 2
                channel_stats['bread_uses'] = max(0, channel_stats['bread_uses'] - 1)
            
            duck['health'] -= bef_damage
            bef_killed = duck['health'] <= 0
            
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
            base_xp = 50 if duck['golden'] else int(self.config.get('default_xp', 10))
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
            response += f" was befriended!   \\_0< QUAACK!   [BEFRIENDED DUCKS: {channel_stats['befriended_ducks']}] [+{xp_gained} xp]"
            self.send_message(channel, self.pm(user, response))
            self.log_action(f"{user} befriended a {'golden ' if duck['golden'] else ''}duck in {channel}")
            self.check_level_change(user, channel, channel_stats, prev_xp)
        else:
            remaining = max(0, duck['health'])
            self.send_message(channel, self.pm(user, f"FRIEND     You comfort the duck. Remaining friendliness needed: {remaining}."))
        
        self.save_player_data()
        self.schedule_next_duck()
    
    def handle_reload(self, user, channel):
        """Handle !reload command"""
        if not self.check_authentication(user):
            return
        
        player = self.get_player(user)
        channel_stats = self.get_channel_stats(user, channel)
        
        if channel_stats['confiscated']:
            self.send_message(channel, self.pm(user, "You are not armed."))
            return
        
        # Only allow reload if out of bullets, jammed, or sabotaged
        if channel_stats['jammed']:
            channel_stats['jammed'] = False
            clip_size = channel_stats.get('clip_size', 10)
            mags_max = channel_stats.get('magazines_max', 2)
            self.send_message(channel, self.pm(user, f"*Crr..CLICK*     You unjam your gun. | Ammo: {channel_stats['ammo']}/{clip_size} | Magazines: {channel_stats['magazines']}/{mags_max}"))
        elif channel_stats['sabotaged']:
            channel_stats['sabotaged'] = False
            clip_size = channel_stats.get('clip_size', 10)
            mags_max = channel_stats.get('magazines_max', 2)
            self.send_message(channel, self.pm(user, f"*Crr..CLICK*     You fix the sabotage. | Ammo: {channel_stats['ammo']}/{clip_size} | Magazines: {channel_stats['magazines']}/{mags_max}"))
        elif channel_stats['ammo'] == 0:
            if channel_stats['magazines'] <= 0:
                self.send_message(channel, self.pm(user, "You have no magazines left to reload with."))
            else:
                clip_size = channel_stats.get('clip_size', 10)
                channel_stats['ammo'] = clip_size
                channel_stats['magazines'] -= 1
                mags_max = channel_stats.get('magazines_max', 2)
                self.send_message(channel, self.pm(user, f"*CLACK CLACK*     You reload. | Ammo: {channel_stats['ammo']}/{clip_size} | Magazines: {channel_stats['magazines']}/{mags_max}"))
        else:
            clip_size = channel_stats.get('clip_size', 10)
            mags_max = channel_stats.get('magazines_max', 2)
            self.send_message(channel, self.pm(user, f"Your gun doesn't need to be reloaded. | Ammo: {channel_stats['ammo']}/{clip_size} | Magazines: {channel_stats['magazines']}/{mags_max}"))
        
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
                    self.send_notice(user, f"You don't have enough XP in {channel}. You need {cost} xp.")
                    return
                channel_stats['xp'] -= cost
                
                # Apply item effects
                if item_id == 1:  # Extra bullet
                    clip_size = channel_stats.get('clip_size', 10)
                    if channel_stats['ammo'] < clip_size:
                        channel_stats['ammo'] = min(clip_size, channel_stats['ammo'] + 1)
                        self.send_message(channel, self.pm(user, f"You just added an extra bullet in your gun in exchange for {item['cost']} xp points. | Ammo: {channel_stats['ammo']}/{clip_size}"))
                    else:
                        self.send_message(channel, self.pm(user, f"Your magazine is already full."))
                        channel_stats['xp'] += item['cost']  # Refund XP
                elif item_id == 2:  # Extra magazine
                    mags_max = channel_stats.get('magazines_max', 2)
                    if channel_stats['magazines'] < mags_max:
                        channel_stats['magazines'] = min(mags_max, channel_stats['magazines'] + 1)
                        self.send_message(channel, self.pm(user, f"You just added an extra magazine in exchange for {item['cost']} xp points. | Magazines: {channel_stats['magazines']}/{mags_max}"))
                    else:
                        self.send_message(channel, self.pm(user, f"You already have the maximum magazines."))
                        channel_stats['xp'] += item['cost']  # Refund XP
                elif item_id == 3:  # AP ammo: next 20 shots do +1 dmg vs golden (i.e., 2 total)
                    ap = channel_stats.get('ap_shots', 0)
                    ex = channel_stats.get('explosive_shots', 0)
                    if ap > 0 and ex == 0:
                        self.send_notice(user, "AP ammo already active. Use it up before buying more.")
                        channel_stats['xp'] += item['cost']
                    else:
                        switched = ex > 0
                        channel_stats['explosive_shots'] = 0
                        channel_stats['ap_shots'] = 20
                        if switched:
                            self.send_message(channel, self.pm(user, "You switched to AP ammo. Next 20 shots are AP."))
                        else:
                            self.send_message(channel, self.pm(user, "You purchased AP ammo. Next 20 shots deal extra damage to golden ducks."))
                elif item_id == 4:  # Explosive ammo: next 20 shots do +1 dmg vs golden and boost accuracy
                    ap = channel_stats.get('ap_shots', 0)
                    ex = channel_stats.get('explosive_shots', 0)
                    if ex > 0 and ap == 0:
                        self.send_notice(user, "Explosive ammo already active. Use it up before buying more.")
                        channel_stats['xp'] += item['cost']
                    else:
                        switched = ap > 0
                        channel_stats['ap_shots'] = 0
                        channel_stats['explosive_shots'] = 20
                        if switched:
                            self.send_message(channel, self.pm(user, "You switched to explosive ammo. Next 20 shots are explosive."))
                        else:
                            self.send_message(channel, self.pm(user, "You purchased explosive ammo. Next 20 shots deal extra damage to golden ducks."))
                elif item_id == 7:  # Sight: next shot accuracy boost; cannot stack
                    if channel_stats.get('sight_next_shot', False):
                        self.send_notice(user, "Sight already mounted for your next shot. Use it before buying more.")
                        channel_stats['xp'] += item['cost']
                    else:
                        channel_stats['sight_next_shot'] = True
                        self.send_message(channel, self.pm(user, "You purchased a sight. Your next shot will be more accurate."))
                elif item_id == 11:  # Sunglasses: 24h protection against mirror / reduce accident penalty
                    channel_stats['sunglasses_until'] = max(channel_stats.get('sunglasses_until', 0), time.time() + 24*3600)
                    self.send_message(channel, self.pm(user, "You put on sunglasses for 24h. You're protected against mirror glare."))
                elif item_id == 12:  # Spare clothes: clear soaked if present
                    if channel_stats.get('soaked_until', 0) > time.time():
                        channel_stats['soaked_until'] = 0
                        self.send_message(channel, self.pm(user, "You change into spare clothes. You're no longer soaked."))
                    else:
                        self.send_notice(user, "You're not soaked. Refunding XP.")
                        channel_stats['xp'] += item['cost']
                elif item_id == 13:  # Brush for gun: unjam, clear sand, and small reliability buff for 24h
                    channel_stats['jammed'] = False
                    # Clear sand debuff if present
                    if channel_stats.get('sand_until', 0) > time.time():
                        channel_stats['sand_until'] = 0
                    channel_stats['brush_until'] = max(channel_stats.get('brush_until', 0), time.time() + 24*3600)
                    self.send_message(channel, self.pm(user, "You clean your gun and remove sand. It feels smoother for 24h."))
                elif item_id == 14:  # Mirror: apply dazzle debuff to target unless countered by sunglasses (target required)
                    if len(args) < 2:
                        self.send_notice(user, "Usage: !shop 14 <nick>")
                        channel_stats['xp'] += item['cost']
                    else:
                        target = args[1]
                        tstats = self.get_channel_stats(target, channel)
                        # If target has sunglasses active, mirror is countered
                        if tstats.get('sunglasses_until', 0) > time.time():
                            self.send_message(channel, self.pm(user, f"{target} is wearing sunglasses. The mirror has no effect."))
                            channel_stats['xp'] += item['cost']
                        else:
                            tstats['mirror_until'] = max(tstats.get('mirror_until', 0), time.time() + 24*3600)
                            self.send_message(channel, self.pm(user, f"You dazzle {target} with a mirror for 24h. Their accuracy is reduced."))
                elif item_id == 15:  # Handful of sand: victim reliability worse for 1h (target required)
                    if len(args) < 2:
                        self.send_notice(user, "Usage: !shop 15 <nick>")
                        channel_stats['xp'] += item['cost']
                    else:
                        target = args[1]
                        tstats = self.get_channel_stats(target, channel)
                        tstats['sand_until'] = max(tstats.get('sand_until', 0), time.time() + 3600)
                        self.send_message(channel, self.pm(user, f"You throw sand into {target}'s gun. Their gun will jam more for 1h."))
                elif item_id == 16:  # Water bucket: soak target for 1h (target required)
                    if len(args) < 2:
                        self.send_notice(user, "Usage: !shop 16 <nick>")
                        channel_stats['xp'] += item['cost']
                    else:
                        target = args[1]
                        tstats = self.get_channel_stats(target, channel)
                        tstats['soaked_until'] = max(tstats.get('soaked_until', 0), time.time() + 3600)
                        self.send_message(channel, self.pm(user, f"You soak {target} with a water bucket. They're out for 1h unless they change clothes."))
                elif item_id == 17:  # Sabotage: jam target immediately (target required)
                    if len(args) < 2:
                        self.send_notice(user, "Usage: !shop 17 <nick>")
                        channel_stats['xp'] += item['cost']
                    else:
                        target = args[1]
                        tstats = self.get_channel_stats(target, channel)
                        tstats['jammed'] = True
                        self.send_message(channel, self.pm(user, f"You sabotage {target}'s weapon. It's jammed."))
                elif item_id == 18:  # Life insurance: protect against confiscation for 24h
                    channel_stats['life_insurance_until'] = max(channel_stats.get('life_insurance_until', 0), time.time() + 24*3600)
                    self.send_message(channel, self.pm(user, "You purchase life insurance. Confiscations will be prevented for 24h."))
                elif item_id == 19:  # Liability insurance: reduce penalties by 50% for 24h
                    channel_stats['liability_insurance_until'] = max(channel_stats.get('liability_insurance_until', 0), time.time() + 24*3600)
                    self.send_message(channel, self.pm(user, "You purchase liability insurance. Penalties reduced by 50% for 24h."))
                elif item_id == 22:  # Upgrade Magazine: increase clip size (level 1-5), dynamic cost per level
                    current_level = channel_stats.get('mag_upgrade_level', 0)
                    if current_level >= 5:
                        self.send_message(channel, self.pm(user, "Your magazine is already fully upgraded."))
                        channel_stats['xp'] += cost
                    else:
                        next_level = current_level + 1
                        channel_stats['mag_upgrade_level'] = next_level
                        # Recompute clip_size via level bonuses so upgrades stack correctly
                        self.apply_level_bonuses(channel_stats)
                        # Top off ammo by 1 up to new clip size
                        channel_stats['ammo'] = min(channel_stats['clip_size'], channel_stats['ammo'] + 1)
                        self.send_message(channel, self.pm(user, f"Upgrade applied. Magazine capacity increased to {channel_stats['clip_size']}."))
                elif item_id == 10:  # Four-leaf clover: +N XP per duck for 24h; single active at a time
                    now = time.time()
                    duration = 24 * 3600
                    if channel_stats.get('clover_until', 0) > now:
                        # Already active; refund
                        self.send_notice(user, "Four-leaf clover already active. Wait until it expires to buy again.")
                        channel_stats['xp'] += item['cost']
                    else:
                        bonus = random.choice([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
                        channel_stats['clover_bonus'] = bonus
                        channel_stats['clover_until'] = now + duration
                        self.send_message(channel, self.pm(user, f"Four-leaf clover activated for 24h. +{bonus} XP per duck."))
                elif item_id == 8:  # Infrared detector: 24h trigger lock window when no duck, limited uses
                    now = time.time()
                    duration = 24 * 3600
                    # Disallow purchase if active and has uses remaining
                    if channel_stats.get('infrared_until', 0) > now and channel_stats.get('infrared_uses', 0) > 0:
                        self.send_notice(user, "Infrared detector already active. Use it up before buying more.")
                        channel_stats['xp'] += item['cost']
                    else:
                        new_until = now + duration
                        channel_stats['infrared_until'] = new_until
                        channel_stats['infrared_uses'] = 6
                        hours = duration // 3600
                        self.send_message(channel, self.pm(user, f"Infrared detector enabled for {hours}h00m. Trigger lock has 6 uses."))
                elif item_id == 20:  # Bread: next 20 befriends count double vs golden
                    if channel_stats.get('bread_uses', 0) > 0:
                        self.send_notice(user, "Bread already active. Use it up before buying more.")
                        channel_stats['xp'] += item['cost']
                    else:
                        channel_stats['bread_uses'] = 20
                        self.send_message(channel, self.pm(user, f"You purchased bread. Next 20 befriends are more effective."))
                elif item_id == 5:  # Repurchase confiscated gun
                    if channel_stats['confiscated']:
                        channel_stats['confiscated'] = False
                        clip_size = channel_stats.get('clip_size', 10)
                        mags_max = channel_stats.get('magazines_max', 2)
                        channel_stats['ammo'] = clip_size
                        channel_stats['magazines'] = mags_max
                        self.send_message(channel, self.pm(user, f"You repurchased your confiscated gun in exchange for {item['cost']} xp points. | Ammo: {clip_size}/{clip_size} | Magazines: {mags_max}/{mags_max}"))
                    else:
                        self.send_message(channel, f"Your gun is not confiscated.")
                        channel_stats['xp'] += item['cost']  # Refund XP
                elif item_id == 21:  # Ducks detector (shop: full 24h duration)
                    now = time.time()
                    duration = 24 * 3600
                    current_until = channel_stats.get('ducks_detector_until', 0)
                    channel_stats['ducks_detector_until'] = max(current_until, now + duration)
                    self.send_message(channel, self.pm(user, "Ducks detector activated for 24h. You'll get a 60s pre-spawn notice."))
                elif item_id == 23:  # Extra Magazine: increase magazines_max (level 1-5), cost scales
                    current_level = channel_stats.get('mag_capacity_level', 0)
                    if current_level >= 5:
                        self.send_message(channel, self.pm(user, "You already carry the maximum extra magazines."))
                        channel_stats['xp'] += item['cost']
                    else:
                        channel_stats['mag_capacity_level'] = current_level + 1
                        channel_stats['magazines_max'] = channel_stats.get('magazines_max', 2) + 1
                        # Grant one extra empty magazine immediately
                        channel_stats['magazines'] = min(channel_stats['magazines_max'], channel_stats['magazines'] + 1)
                        self.send_message(channel, self.pm(user, f"Upgrade applied. You can now carry {channel_stats['magazines_max']} magazines."))
                        item['cost'] = min(1000, item['cost'] + 200)
                else:
                    # For other items, just show generic message
                    self.send_message(channel, self.pm(user, f"You purchased {item['name']} in exchange for {item['cost']} xp points."))
                
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
        stats_text += f"[Profile]  {channel_stats['xp']} xp | lvl {channel_level} | accuracy: {acc_pct}% | karma: {player['karma']:.2f}% good hunter  "
        channel_best = f"{channel_stats['best_time']:.3f}s" if channel_stats['best_time'] else "N/A"
        total_best = f"{best_time:.3f}s" if best_time else "N/A"
        channel_avg = channel_stats['total_reaction_time']/max(1,channel_stats['shots_fired'])
        
        stats_text += f"[Channel Stats]  {channel_stats['ducks_shot']} ducks (incl. {channel_stats['golden_ducks']} golden) | best time: {channel_best} | avg react: {channel_avg:.3f}s  "
        stats_text += f"[Total Stats]  {total_ducks} ducks (incl. {total_golden} golden) | {total_xp} xp | best time: {total_best} | avg react: {avg_reaction:.3f}s"

        # Show consumables with remaining counts
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
        # Infrared detector remaining time
        now = time.time()
        infrared_until = channel_stats.get('infrared_until', 0)
        if infrared_until and infrared_until > now:
            remaining = int(infrared_until - now)
            hours = remaining // 3600
            parts.append(f"Infrared Detector [{hours}/24h]")
        # Infrared uses display
        ir_uses = channel_stats.get('infrared_uses', 0)
        if infrared_until and infrared_until > now and ir_uses > 0:
            parts.append(f"Infrared Uses [{ir_uses}/6]")
        if parts:
            stats_text += "  |  Consumables: " + " | ".join(parts)
        # Show sight if active (not really a consumable with count, but short-lived effect)
        if channel_stats.get('sight_next_shot', False):
            stats_text += "  |  Sight [next shot]"
        
        self.send_notice(user, stats_text)
    
    def handle_topduck(self, user, channel, args):
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
        
        self.send_message(channel, top_text)
    
    def handle_duckhelp(self, user, channel):
        """Handle !duckhelp command"""
        help_text = "Duck Hunt Commands: !bang, !bef, !reload, !shop, !duckstats, !topduck [duck], !lastduck, !duckhelp"
        self.send_notice(user, help_text)
    
    def handle_lastduck(self, user, channel):
        """Handle !lastduck command"""
        if not self.check_authentication(user):
            self.send_message(channel, f"{user}: You must be authenticated to play.")
            return
        
        player = self.get_player(user)
        channel_stats = self.get_channel_stats(user, channel)
        
        if not channel_stats['last_duck_time']:
            self.send_message(channel, f"{user}: You haven't shot any ducks in {channel} yet.")
            return
        
        current_time = time.time()
        time_diff = current_time - channel_stats['last_duck_time']
        
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
        
        self.send_message(channel, f"{user} > The last duck was seen in {channel}: {time_str} ago.")
    
    def handle_admin_command(self, user, channel, command, args):
        """Handle admin commands"""
        if not self.is_admin(user) and not self.is_owner(user):
            self.send_notice(user, "You don't have permission to use admin commands.")
            return
        
        if command == "spawnduck":
            count = 1
            if args and args[0].isdigit():
                count = min(int(args[0]), self.max_ducks)
            
            spawned = 0
            norm_channel = self.normalize_channel(channel)
            with self.ducks_lock:
                if norm_channel not in self.active_ducks:
                    self.active_ducks[norm_channel] = []
                remaining_capacity = max(0, self.max_ducks - len(self.active_ducks[norm_channel]))
            to_spawn = min(count, remaining_capacity)
            for _ in range(to_spawn):
                self.spawn_duck(channel)
                spawned += 1
            
            if spawned > 0:
                self.log_action(f"{user} spawned {spawned} duck(s) in {channel}.")
            else:
                self.send_notice(user, f"Cannot spawn ducks in {channel} - already at maximum ({self.max_ducks})")
        elif command == "spawngold":
            # Spawn a golden duck (respect per-channel capacity)
            with self.ducks_lock:
                norm_channel = self.normalize_channel(channel)
                if norm_channel not in self.active_ducks:
                    self.active_ducks[norm_channel] = []
                if len(self.active_ducks[norm_channel]) >= self.max_ducks:
                    self.send_notice(user, f"Cannot spawn golden duck in {channel} - already at maximum ({self.max_ducks})")
                    return
                golden_duck = {'golden': True, 'health': 5, 'spawn_time': time.time()}
                self.active_ducks[norm_channel].append(golden_duck)
            duck_art = "-.,¸¸.-·°'`'°·-.,¸¸.-·°'`'°· \\_O<   QUACK   * GOLDEN DUCK DETECTED *"
            self.send_message(channel, duck_art)
            self.log_action(f"{user} spawned golden duck in {channel}")
            self.schedule_next_duck()
        elif command == "rearm" and args:
            target = args[0]
            if target in self.players:
                channel_stats = self.get_channel_stats(target, channel)
                channel_stats['confiscated'] = False
                clip_size = channel_stats.get('clip_size', 10)
                mags_max = channel_stats.get('magazines_max', 2)
                channel_stats['ammo'] = clip_size
                channel_stats['magazines'] = mags_max
                self.send_message(channel, f"{target} has been rearmed.")
                self.save_player_data()
        elif command == "disarm" and args:
            target = args[0]
            if target in self.players:
                channel_stats = self.get_channel_stats(target, channel)
                channel_stats['confiscated'] = True
                # Optionally also empty ammo
                channel_stats['ammo'] = 0
                self.send_message(channel, f"{target} has been disarmed.")
                self.save_player_data()
    
    def handle_owner_command(self, user, command, args):
        """Handle owner commands via PRIVMSG"""
        self.log_action(f"handle_owner_command called: user={user}, command={command}")
        if not self.is_owner(user):
            self.log_action(f"User {user} is not owner")
            self.send_notice(user, "You don't have permission to use owner commands.")
            return
        self.log_action(f"User {user} is owner, processing command {command}")
        
        if command == "add" and len(args) >= 2:
            if args[0] == "owner":
                # Add owner logic
                self.send_notice(user, f"Added {args[1]} to owner list.")
            elif args[0] == "admin":
                # Add admin logic
                self.send_notice(user, f"Added {args[1]} to admin list.")
        elif command == "disarm" and len(args) >= 2:
            target = args[0]
            channel = args[1]
            if target in self.players:
                channel_stats = self.get_channel_stats(target, channel)
                channel_stats['confiscated'] = True
                channel_stats['ammo'] = 0
                self.send_notice(user, f"{target} has been disarmed in {channel}.")
                self.save_player_data()
        elif command == "reload":
            self.load_config("duckhunt.conf")
            self.send_notice(user, "Configuration reloaded.")
        elif command == "restart":
            self.log_action(f"Restart command received from {user}")
            self.send_notice(user, "Restarting bot...")
            self.log_action(f"{user} restarted the bot.")
            # Save data before restart
            self.save_player_data()
            # Close connection and exit
            self.sock.close()
            exit(0)
        elif command == "join" and args:
            channel = args[0]
            self.send(f"JOIN {channel}")
            self.channels[channel] = set()
            self.send_notice(user, f"Joined {channel}")
        elif command == "clear" and args:
            channel = args[0]
            if channel not in self.channels:
                self.send_notice(user, f"Channel {channel} not found.")
                return
            
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
            with self.ducks_lock:
                if norm_channel in self.active_ducks:
                    del self.active_ducks[norm_channel]
            
            self.send_notice(user, f"Cleared all data for {channel} ({cleared_count} players affected).")
            self.log_action(f"{user} cleared all data for {channel}")
            self.save_player_data()
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
            self.registered = True
            # Set a timeout for MOTD completion (30 seconds)
            self.motd_start_time = time.time()
            return
        
        # Handle MOTD end (376 message) - now we can complete registration
        if "376" in data and "End of /MOTD command" in data:
            self.complete_registration()
            return
        
        # Count MOTD messages and force completion after too many
        if self.registered and hasattr(self, 'motd_start_time') and not hasattr(self, 'registration_complete'):
            if "372" in data or "375" in data or "376" in data:
                self.motd_message_count += 1
                if self.motd_message_count > 50:  # Force completion after 50 MOTD messages
                    self.log_action(f"MOTD message limit reached ({self.motd_message_count} messages) - completing registration")
                    self.motd_timeout_triggered = True
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
        # Command aliases / typos
        if command in ["spawduck", "spawn", "sd"]:
            command = "spawnduck"
        elif command in ["spawng", "sg"]:
            command = "spawngold"
        
        if command == "bang":
            self.handle_bang(user, channel)
        elif command == "bef":
            self.handle_bef(user, channel)
        elif command == "reload":
            self.handle_reload(user, channel)
        elif command == "shop":
            self.handle_shop(user, channel, args)
        elif command == "duckstats":
            self.handle_duckstats(user, channel, args)
        elif command == "topduck":
            self.handle_topduck(user, channel, args)
        elif command == "lastduck":
            self.handle_lastduck(user, channel)
        elif command == "duckhelp":
            self.handle_duckhelp(user, channel)
        elif command in ["spawnduck", "spawngold", "rearm", "disarm"]:
            self.handle_admin_command(user, channel, command, args)

    # --- Loot System ---
    def apply_weighted_loot(self, user: str, channel: str, channel_stats: dict) -> None:
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

        def say(msg: str) -> None:
            self.send_message(channel, self.pm(user, msg))

        if choice == "extra_bullet":
            if channel_stats['ammo'] < clip_size:
                channel_stats['ammo'] = min(clip_size, channel_stats['ammo'] + 1)
                say(f"By searching the bushes, you find an extra bullet! | Ammo: {channel_stats['ammo']}/{clip_size}")
            else:
                xp = 7
                channel_stats['xp'] += xp
                say(f"By searching the bushes, you find an extra bullet! Your magazine is full, so you gain {xp} XP instead.")
        elif choice == "extra_mag":
            if channel_stats['magazines'] < mags_max:
                channel_stats['magazines'] = min(mags_max, channel_stats['magazines'] + 1)
                say(f"By searching the bushes, you find an extra ammo clip! | Magazines: {channel_stats['magazines']}/{mags_max}")
            else:
                xp = 20
                channel_stats['xp'] += xp
                say(f"By searching the bushes, you find an extra ammo clip! You already have maximum magazines, so you gain {xp} XP instead.")
        elif choice == "sight_next":
            # If already active, convert to XP equal to shop price (shop_sight)
            if channel_stats.get('sight_next_shot', False):
                sight_cost = int(self.config.get('shop_sight', 6))
                channel_stats['xp'] += sight_cost
                say(f"You find a sight, but you already have one mounted for your next shot. [+{sight_cost} xp]")
            else:
                channel_stats['sight_next_shot'] = True
                say("By searching the bushes, you find a sight for your gun! Your next shot will be more accurate.")
        elif choice == "silencer":
            if channel_stats.get('silencer_until', 0) > now:
                cost = int(self.config.get('shop_silencer', 5))
                channel_stats['xp'] += cost
                say(f"You find a silencer, but you already have one active. [+{cost} xp]")
            else:
                channel_stats['silencer_until'] = now + day
                say("By searching the bushes, you find a silencer! It will prevent frightening ducks for 24h.")
        elif choice == "ducks_detector":
            if channel_stats.get('ducks_detector_until', 0) > now:
                cost = int(self.config.get('shop_ducks_detector', 50))
                channel_stats['xp'] += cost
                say(f"You find a ducks detector, but you already have one active. [+{cost} xp]")
            else:
                channel_stats['ducks_detector_until'] = now + day
                say("By searching the bushes, you find a ducks detector! You'll get a 60s pre-spawn notice for 24h.")
        elif choice == "ap_ammo":
            if channel_stats.get('ap_shots', 0) > 0:
                xp = int(self.config.get('shop_ap_ammo', 15))
                channel_stats['xp'] += xp
                say(f"You find AP ammo, but you already have some. [+{xp} xp]")
            else:
                channel_stats['explosive_shots'] = 0
                channel_stats['ap_shots'] = 20
                say("By searching the bushes, you find AP ammo! Next 20 shots deal extra damage to golden ducks.")
        elif choice == "explosive_ammo":
            if channel_stats.get('explosive_shots', 0) > 0:
                xp = int(self.config.get('shop_explosive_ammo', 25))
                channel_stats['xp'] += xp
                say(f"You find explosive ammo, but you already have some. [+{xp} xp]")
            else:
                channel_stats['ap_shots'] = 0
                channel_stats['explosive_shots'] = 20
                say("By searching the bushes, you find explosive ammo! Next 20 shots deal extra damage to golden ducks.")
        elif choice == "grease":
            if channel_stats.get('grease_until', 0) > now:
                cost = int(self.config.get('shop_grease', 8))
                channel_stats['xp'] += cost
                say(f"You find grease, but you already have some applied. [+{cost} xp]")
            else:
                channel_stats['grease_until'] = now + day
                say("By searching the bushes, you find grease! Your gun will jam half as often for 24h.")
        elif choice == "sunglasses":
            if channel_stats.get('sunglasses_until', 0) > now:
                cost = int(self.config.get('shop_sunglasses', 5))
                channel_stats['xp'] += cost
                say(f"You find sunglasses, but you're already wearing some. [+{cost} xp]")
            else:
                channel_stats['sunglasses_until'] = now + day
                say("By searching the bushes, you find sunglasses! You're protected against bedazzlement for 24h.")
        elif choice == "infrared":
            if channel_stats.get('infrared_until', 0) > now and channel_stats.get('infrared_uses', 0) > 0:
                cost = int(self.config.get('shop_infrared_detector', 15))
                channel_stats['xp'] += cost
                say(f"You find an infrared detector, but yours is still active. [+{cost} xp]")
            else:
                channel_stats['infrared_until'] = now + day
                channel_stats['infrared_uses'] = max(channel_stats.get('infrared_uses', 0), 6)
                say("By searching the bushes, you find an infrared detector! Trigger locks when no duck (6 uses, 24h).")
        elif choice == "wallet_150xp":
            xp = 150
            channel_stats['xp'] += xp
            # Try to pick a random victim name from channel
            victim = None
            if channel in self.channels and self.channels[channel]:
                victim = random.choice(list(self.channels[channel]))
            owner_text = f" {victim}'s" if victim else " a"
            say(f"By searching the bushes, you find{owner_text} lost wallet! [+{xp} xp]")
        elif choice == "hunting_mag":
            xp_options = [10, 20, 40, 50, 100]
            xp = random.choice(xp_options)
            channel_stats['xp'] += xp
            say(f"By searching the bushes, you find a hunting magazine! [+{xp} xp]")
        elif choice == "clover":
            # If already active, convert to XP equal to shop price
            if channel_stats.get('clover_until', 0) > now:
                clover_cost = int(self.config.get('shop_four_leaf_clover', 13))
                channel_stats['xp'] += clover_cost
                say(f"You find a four-leaf clover, but you already have its luck active. [+{clover_cost} xp]")
            else:
                options = [1, 3, 5, 7, 8, 9, 10]
                bonus = random.choice(options)
                channel_stats['clover_bonus'] = bonus
                channel_stats['clover_until'] = max(channel_stats.get('clover_until', 0), now + day)
                say(f"By searching the bushes, you find a four-leaf clover! +{bonus} XP per duck for 24h.")
        else:  # junk
            junk_items = [
                "discarded tire", "old shoe", "creepy crawly", "pile of rubbish", "cigarette butt",
                "broken compass", "expired hunting license", "rusty can", "tangled fishing line",
            ]
            junk = random.choice(junk_items)
            say(f"By searching the bushes, you find a {junk}. It's worthless.")

        self.save_player_data()
    
    def handle_private_message(self, user, message):
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
            self.handle_owner_command(user, command, args)
    
    def run(self):
        """Main bot loop"""
        self.connect()
        
        while True:
            try:
                data = self.sock.recv(1024).decode('utf-8')
                if data:
                    # Process each line
                    for line in data.split('\r\n'):
                        if line.strip():
                            self.process_message(line)
                            self.message_count += 1
                
                # Check for MOTD timeout (30 seconds) or message limit (100 messages)
                if self.registered and hasattr(self, 'motd_start_time') and not hasattr(self, 'registration_complete') and not self.motd_timeout_triggered:
                    elapsed = time.time() - self.motd_start_time
                    if elapsed > 30 or self.message_count > 100:
                        self.log_action(f"MOTD timeout ({elapsed:.1f}s, {self.message_count} messages) - completing registration")
                        self.motd_timeout_triggered = True
                        self.complete_registration()
                    elif elapsed > 25:  # Debug logging
                        self.log_action(f"MOTD timeout approaching: {elapsed:.1f}s elapsed ({self.message_count} messages)")
                
                # Check for duck spawn (only after registration)
                # Send pre-spawn notice 60s before spawn time
                if hasattr(self, 'registration_complete') and self.duck_spawn_time and not self.next_spawn_notice_sent:
                    now = time.time()
                    if self.pre_spawn_notice_time and now >= self.pre_spawn_notice_time:
                        self.notify_duck_detector()
                        self.next_spawn_notice_sent = True
                # Perform the actual spawn
                if hasattr(self, 'registration_complete') and self.duck_spawn_time and time.time() >= self.duck_spawn_time:
                    # Use the preselected channel if available
                    if self.next_spawn_channel:
                        self.spawn_duck(self.next_spawn_channel)
                    else:
                        self.spawn_duck()
                    self.duck_spawn_time = None
                    self.next_spawn_channel = None
                    self.pre_spawn_notice_time = None
                    self.next_spawn_notice_sent = False
                elif hasattr(self, 'registration_complete') and not self.duck_spawn_time:
                    # Debug: registration complete but no spawn time set
                    self.log_action("DEBUG: Registration complete but no duck spawn time set - scheduling now")
                    self.schedule_next_duck()
                
                # Duck despawn is handled in the exception handler with proper throttling
                
            except socket.error as e:
                if e.errno == 11:  # EAGAIN/EWOULDBLOCK - no data available
                    # Check for MOTD timeout (30 seconds)
                    if self.registered and hasattr(self, 'motd_start_time') and not hasattr(self, 'registration_complete') and not self.motd_timeout_triggered:
                        elapsed = time.time() - self.motd_start_time
                        if elapsed > 30:
                            self.log_action(f"MOTD timeout ({elapsed:.1f}s) - completing registration")
                            self.motd_timeout_triggered = True
                            self.complete_registration()
                        elif elapsed > 25:  # Debug logging
                            self.log_action(f"MOTD timeout approaching (no data): {elapsed:.1f}s elapsed")
                    
                    # Check for duck spawn (only after registration)
                    # Pre-spawn notice handling during idle
                    if hasattr(self, 'registration_complete') and self.duck_spawn_time and not self.next_spawn_notice_sent:
                        now = time.time()
                        if self.pre_spawn_notice_time and now >= self.pre_spawn_notice_time:
                            self.notify_duck_detector()
                            self.next_spawn_notice_sent = True
                    # Spawn at scheduled time
                    if hasattr(self, 'registration_complete') and self.duck_spawn_time and time.time() >= self.duck_spawn_time:
                        if self.next_spawn_channel:
                            self.spawn_duck(self.next_spawn_channel)
                        else:
                            self.spawn_duck()
                        self.duck_spawn_time = None
                        self.next_spawn_channel = None
                        self.pre_spawn_notice_time = None
                        self.next_spawn_notice_sent = False
                    
                    # Check for duck despawn (only after registration, throttled to once per second)
                    if hasattr(self, 'registration_complete'):
                        current_time = time.time()
                        if current_time - self.last_despawn_check >= 1.0:
                            self.despawn_old_ducks()
                            self.last_despawn_check = current_time
                    
                    time.sleep(0.1)  # Small delay to prevent busy waiting
                    continue
                else:
                    self.log_action(f"Socket error: {e}")
                    break
            except Exception as e:
                self.log_action(f"Error: {e}")
                break
        
        self.sock.close()

if __name__ == "__main__":
    bot = DuckHuntBot()
    bot.run()
