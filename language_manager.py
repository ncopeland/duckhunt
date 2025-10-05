#!/usr/bin/env python3
"""
Language Manager for DuckHunt Bot
Handles loading and managing multiple language resource files
"""

import json
import os
from typing import Dict, Optional

class LanguageManager:
    def __init__(self, languages_dir="languages"):
        self.languages_dir = languages_dir
        self.languages = {}
        self.user_languages = {}  # {username: language_code}
        self.default_language = "en"
        self.load_languages()
    
    def load_languages(self):
        """Load all language files from the languages directory"""
        if not os.path.exists(self.languages_dir):
            print(f"Warning: Languages directory '{self.languages_dir}' not found")
            return
        
        for filename in os.listdir(self.languages_dir):
            if filename.endswith('.json'):
                lang_code = filename[:-5]  # Remove .json extension
                try:
                    filepath = os.path.join(self.languages_dir, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        self.languages[lang_code] = json.load(f)
                    print(f"Loaded language: {lang_code} - {self.languages[lang_code].get('language_name', 'Unknown')}")
                except Exception as e:
                    print(f"Error loading language file {filename}: {e}")
    
    def get_available_languages(self) -> Dict[str, str]:
        """Return dict of {code: name} for all available languages"""
        return {code: data.get('language_name', code) 
                for code, data in self.languages.items()}
    
    def set_user_language(self, username: str, language_code: str) -> bool:
        """Set language preference for a user"""
        if language_code in self.languages:
            self.user_languages[username.lower()] = language_code
            return True
        return False
    
    def get_user_language(self, username: str) -> str:
        """Get user's language preference, or default"""
        return self.user_languages.get(username.lower(), self.default_language)
    
    def get_text(self, username: str, key_path: str, colorize_func=None, **kwargs) -> str:
        """
        Get translated text for a user
        key_path: dot-separated path like 'bang.not_armed' or 'shop.invalid_id'
        colorize_func: function to apply IRC color codes (from bot)
        kwargs: values to format into the string
        """
        lang_code = self.get_user_language(username)
        lang_data = self.languages.get(lang_code, self.languages.get(self.default_language, {}))
        
        # Navigate through nested dict
        keys = key_path.split('.')
        current = lang_data
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
                if current is None:
                    # Fallback to English
                    current = self.languages.get(self.default_language, {})
                    for fallback_key in keys:
                        if isinstance(current, dict):
                            current = current.get(fallback_key)
                            if current is None:
                                return f"[Missing translation: {key_path}]"
                    break
            else:
                return f"[Invalid key path: {key_path}]"
        
        if current is None:
            return f"[Missing translation: {key_path}]"
        
        # Format string with kwargs if it's a string
        if isinstance(current, str):
            # First apply colorization markers if colorize_func provided
            if colorize_func:
                current = self._apply_color_markers(current, colorize_func)
            
            # Then format with kwargs
            if kwargs:
                try:
                    return current.format(**kwargs)
                except KeyError as e:
                    print(f"Warning: Missing format key {e} in '{key_path}' for language {lang_code}")
                    return current
        
        return str(current)
    
    def _apply_color_markers(self, text: str, colorize_func) -> str:
        """
        Parse and apply color markers like {{red:text}} or {{red,bold:text}}
        Markers format: {{color:text}} or {{color,bold:text}} or {{reset}}
        """
        import re
        
        # Pattern to match {{color:text}} or {{color,bold:text}}
        pattern = r'\{\{([^:}]+):([^}]+)\}\}'
        
        def replace_marker(match):
            style_spec = match.group(1)
            content = match.group(2)
            
            # Parse style spec
            parts = [p.strip() for p in style_spec.split(',')]
            color = None
            bold = False
            
            for part in parts:
                if part == 'bold':
                    bold = True
                elif part in ['red', 'green', 'yellow', 'blue', 'purple', 'grey', 'orange', 
                             'cyan', 'white', 'black', 'brown', 'lime', 'light_cyan', 
                             'light_blue', 'pink', 'light_grey']:
                    color = part
            
            return colorize_func(content, color=color, bold=bold)
        
        # Replace all color markers
        result = re.sub(pattern, replace_marker, text)
        
        # Handle {{reset}} markers
        result = result.replace('{{reset}}', '\x0f')
        
        return result
    
    def get_command(self, username: str, command: str) -> str:
        """Get localized command name"""
        return self.get_text(username, f'commands.{command}')
    
    def save_user_preferences(self, filename="language_prefs.json"):
        """Save user language preferences to file"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.user_languages, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving language preferences: {e}")
    
    def load_user_preferences(self, filename="language_prefs.json"):
        """Load user language preferences from file"""
        if os.path.exists(filename):
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    self.user_languages = json.load(f)
                print(f"Loaded language preferences for {len(self.user_languages)} users")
            except Exception as e:
                print(f"Error loading language preferences: {e}")

