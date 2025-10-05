# Multilanguage Support Roadmap

## Status: Foundation Complete ✓

### Completed
- ✓ Created `languages/` directory structure
- ✓ Created English base template (`languages/en.json`)
- ✓ Created 24 additional language stub files ready for translation
- ✓ Created `LanguageManager` class (`language_manager.py`)
- ✓ Defined all message keys and structure

### Supported Languages (25 total)
1. English (en) - ✓ Complete
2. Mandarin Chinese (zh-CN) - Stub ready
3. Hindi (hi) - Stub ready
4. Spanish (es) - Stub ready
5. French (fr) - Stub ready
6. Modern Standard Arabic (ar) - Stub ready
7. Portuguese (pt) - Stub ready
8. Bengali (bn) - Stub ready
9. Russian (ru) - Stub ready
10. Urdu (ur) - Stub ready
11. Indonesian (id) - Stub ready
12. German (de) - Stub ready
13. Japanese (ja) - Stub ready
14. Nigerian Pidgin (pcm) - Stub ready
15. Marathi (mr) - Stub ready
16. Egyptian Arabic (arz) - Stub ready
17. Telugu (te) - Stub ready
18. Turkish (tr) - Stub ready
19. Tamil (ta) - Stub ready
20. Cantonese (yue) - Stub ready
21. Vietnamese (vi) - Stub ready
22. Wu Chinese (wuu) - Stub ready
23. Tagalog (tl) - Stub ready
24. Korean (ko) - Stub ready
25. Farsi (fa) - Stub ready

## Phase 1: Integration (TODO)
This requires refactoring ~500+ hardcoded strings in `duckhunt_bot.py`

### Core Integration Steps
1. Import LanguageManager into DuckHuntBot class
2. Initialize language manager in `__init__`
3. Add `!ducklang [code]` command handler
4. Replace hardcoded strings with `lang.get_text()` calls

### Critical Areas to Refactor (in priority order)
1. **!bang command** (~50 messages)
   - Lines 1445-1703
   - not_armed, gun_jammed, empty_magazine, trigger_locked, missed, golden_hit, duck_killed, etc.

2. **!bef command** (~10 messages)
   - Lines 1705-1798
   - no_duck, failed, success, golden_detected, etc.

3. **!reload command** (~6 messages)
   - Lines 1800-1837
   - unjam, reloaded, no_need, etc.

4. **!shop command** (~80 messages)
   - Lines 1839-2139
   - All shop item purchase messages, errors, confirmations

5. **!duckstats command** (~10 messages)
   - Lines 2984-3127
   - stats display format

6. **!topduck command** (~5 messages)
   - Lines 2888-2982
   - scoreboard display

7. **Level/Promotion messages** (~5 messages)
   - Lines 1182-1197
   - promotion, demotion announcements

8. **Loot system** (~30 messages)
   - Lines 2611-2772
   - All loot drop announcements

9. **Admin commands** (~10 messages)
   - Lines 2177-2248
   - admin feedback messages

10. **Owner commands** (~20 messages)
    - Lines 2250-2453
    - owner command responses

### Example Refactor Pattern

**Before:**
```python
await self.send_message(network, channel, self.pm(user, "You are not armed."))
```

**After:**
```python
msg = self.lang.get_text(user, 'bang.not_armed')
await self.send_message(network, channel, self.pm(user, msg))
```

**With variables:**
```python
msg = self.lang.get_text(user, 'bang.empty_magazine', 
                         mag_capacity=mag_capacity, 
                         magazines=magazines, 
                         mags_max=mags_max)
await self.send_message(network, channel, self.pm(user, msg))
```

## Phase 2: Testing
1. Test `!ducklang` command
2. Test each command with different languages
3. Verify format string replacements work correctly
4. Test fallback to English for missing translations

## Phase 3: Translation
1. Translate stub files to actual languages (can be crowdsourced)
2. Consider using translation services for initial pass
3. Have native speakers review and refine translations

## Phase 4: Documentation
1. Update README with multilanguage support info
2. Document how to add new languages
3. Document translation contribution process

## Implementation Notes
- User language preferences stored in `language_prefs.json`
- Language changes are per-user, not per-channel
- Fallback to English if translation missing
- All 25 language files use UTF-8 encoding
- Command names can also be localized (e.g., `!dispara` for Spanish `!bang`)

## File Structure
```
duckhunt/
├── duckhunt_bot.py          # Main bot (needs refactoring)
├── language_manager.py      # Language system (✓ complete)
├── language_prefs.json      # User preferences (auto-generated)
└── languages/
    ├── en.json             # English (✓ complete)
    ├── es.json             # Spanish (stub)
    ├── zh-CN.json          # Mandarin (stub)
    ├── hi.json             # Hindi (stub)
    └── ... (21 more stubs)
```

## Estimated Effort
- Phase 1 (Integration): 8-12 hours of careful refactoring
- Phase 2 (Testing): 2-4 hours
- Phase 3 (Translation): Varies (can be community effort)
- Phase 4 (Documentation): 1-2 hours

**Total bot refactoring: ~500-600 string replacements across 3261 lines**

This is a major undertaking that should be done incrementally and tested thoroughly at each stage.

