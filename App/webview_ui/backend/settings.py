"""
Settings management for OpenCode Token Meter
"""
import json
import os
import shutil
import platform
import copy

APP_NAME = "OpenCode Token Meter"
SYSTEM = platform.system()

# Platform-specific base directory
if SYSTEM == "Darwin":  # macOS
    BASE_DIR = os.path.join(os.path.expanduser("~"), "Library", "Application Support", APP_NAME)
elif SYSTEM == "Windows":
    # Use APPDATA (Roaming) for user-specific application data
    appdata = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Roaming")
    BASE_DIR = os.path.join(appdata, APP_NAME)
else:  # Linux and other Unix-like systems
    BASE_DIR = os.path.join(os.path.expanduser("~"), ".local", "share", APP_NAME)

# Migration: The previous version used macOS-style path on Windows
OLD_SETTINGS_PATH = os.path.join(
    os.path.expanduser("~"),
    "Library", "Application Support", APP_NAME, "settings.json"
)

SETTINGS_PATH = os.path.join(BASE_DIR, "settings.json")

DEFAULT_SETTINGS = {
    "version": "1.0.1",  # App version - update this when releasing new versions
    "timezone": "local", # "local", "UTC", or specific timezone string like "Asia/Hong_Kong"
    "default_time_scope": "week", # Default dashboard view: "today", "week", "month", "all"
    "prices": {
        "default": {
            "input": 0.5,      # $ per 1M tokens (Gemini 3 Flash default)
            "output": 3.0,     # $ per 1M tokens
            "caching": 0.05,   # $ per 1M tokens (read + write)
            "request": 0.0     # $ per request
        },
        "models": {
            # Anthropic - Sorted alphabetically
            "anthropic/claude-haiku-4-5": {
                "input": 1.0,
                "output": 5.0,
                "caching": 0.10,
                "request": 0.0,
                "provider": "anthropic"
            },
            "anthropic/claude-opus-4-1": {
                "input": 15.0,
                "output": 75.0,
                "caching": 1.50,
                "request": 0.0,
                "provider": "anthropic"
            },
            "anthropic/claude-opus-4-5": {
                "input": 5.0,
                "output": 25.0,
                "caching": 0.50,
                "request": 0.0,
                "provider": "anthropic"
            },
            "anthropic/claude-opus-4-6": {
                "input": 5.0,
                "output": 25.0,
                "caching": 0.50,
                "request": 0.0,
                "provider": "anthropic"
            },
            "anthropic/claude-sonnet-4-5": {
                "input": 3.0,
                "output": 15.0,
                "caching": 0.30,
                "request": 0.0,
                "provider": "anthropic"
            },
            # GitHub Copilot - Sorted alphabetically by model name
            "github-copilot/claude-haiku-4.5": {
                "input": 0.0,
                "output": 0.0,
                "caching": 0.0,
                "request": 0.0132,
                "provider": "github-copilot"
            },
            "github-copilot/claude-opus-4.5": {
                "input": 0.0,
                "output": 0.0,
                "caching": 0.0,
                "request": 0.12,
                "provider": "github-copilot"
            },
            "github-copilot/claude-sonnet-4.5": {
                "input": 0.0,
                "output": 0.0,
                "caching": 0.0,
                "request": 0.04,
                "provider": "github-copilot"
            },
            "github-copilot/gemini-3-flash-preview": {
                "input": 0.0,
                "output": 0.0,
                "caching": 0.0,
                "request": 0.0132,
                "provider": "github-copilot"
            },
            "github-copilot/gemini-3-pro-preview": {
                "input": 0.0,
                "output": 0.0,
                "caching": 0.0,
                "request": 0.04,
                "provider": "github-copilot"
            },
            "github-copilot/gpt-5-mini": {
                "input": 0.0,
                "output": 0.0,
                "caching": 0.0,
                "request": 0.0,
                "provider": "github-copilot"
            },
            "github-copilot/gpt-5.2-codex": {
                "input": 0.0,
                "output": 0.0,
                "caching": 0.0,
                "request": 0.04,
                "provider": "github-copilot"
            },
            # Google - Sorted alphabetically
            "google/gemini-3-flash-preview": {
                "input": 0.5,
                "output": 3.0,
                "caching": 0.05,
                "request": 0.0,
                "provider": "google"
            },
            "google/gemini-3-pro": {
                "input": 2.5,
                "output": 15.0,
                "caching": 0.25,
                "request": 0.0,
                "provider": "google"
            },
            # NVIDIA - Sorted alphabetically
            "nvidia/minimaxai/minimax-m2.1": {
                "input": 0.0,
                "output": 0.0,
                "caching": 0.0,
                "request": 0.0,
                "provider": "nvidia"
            },
            "nvidia/openai/gpt-oss-120b": {
                "input": 0.0,
                "output": 0.0,
                "caching": 0.0,
                "request": 0.0,
                "provider": "nvidia"
            },
            "nvidia/z-ai/glm4.7": {
                "input": 0.0,
                "output": 0.0,
                "caching": 0.0,
                "request": 0.0,
                "provider": "nvidia"
            },
            # OpenCode - Sorted alphabetically (all models are FREE)
            "opencode/glm-4.7-free": {
                "input": 0.0,
                "output": 0.0,
                "caching": 0.0,
                "request": 0.0,
                "provider": "opencode"
            },
            "opencode/gpt-5-nano": {
                "input": 0.0,
                "output": 0.0,
                "caching": 0.0,
                "request": 0.0,
                "provider": "opencode"
            },
            "opencode/kimi-k2.5-free": {
                "input": 0.0,
                "output": 0.0,
                "caching": 0.0,
                "request": 0.0,
                "provider": "opencode"
            },
            "opencode/minimax-m2.1-free": {
                "input": 0.0,
                "output": 0.0,
                "caching": 0.0,
                "request": 0.0,
                "provider": "opencode"
            }
        },
        "deleted_models": [],
        "known_default_models": []
    },
    "thresholds": {
        "enabled": False,
        "daily_tokens": 1000000,    # 1M tokens (1000K)
        "daily_cost": 20.0,          # $20
        "monthly_tokens": 10000000,  # 10M tokens (10000K)
        "monthly_cost": 1000.0,      # $1000
        "monthly_reset_day": 1       # Day of month (1-31)
    },
    "refresh_interval": 300,  # 5 minutes
    "notifications_enabled": True
}

class Settings:
    """Settings manager with persistence and migration"""
    
    def __init__(self):
        self._migrate_if_needed()
        self.settings = self._load()
        if self._normalize_model_settings():
            self.save()
    
    def _migrate_if_needed(self):
        """Migrate settings from old path to new path if needed"""
        if os.path.exists(OLD_SETTINGS_PATH) and not os.path.exists(SETTINGS_PATH):
            try:
                # Create new directory
                os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
                # Copy settings file
                shutil.copy2(OLD_SETTINGS_PATH, SETTINGS_PATH)
                print(f"Migrated settings from {OLD_SETTINGS_PATH} to {SETTINGS_PATH}")
            except Exception as e:
                print(f"Failed to migrate settings: {e}")
    
    def _load(self):
        """Load settings from file or return defaults"""
        if os.path.exists(SETTINGS_PATH):
            try:
                with open(SETTINGS_PATH, 'r') as f:
                    loaded = json.load(f)
                    # Deep merge with defaults, but preserve user's models (don't merge DEFAULT models)
                    result = self._smart_merge(copy.deepcopy(DEFAULT_SETTINGS), loaded)
                    return result
            except:
                pass
        return copy.deepcopy(DEFAULT_SETTINGS)

    def reload(self):
        """Reload settings from file"""
        self.settings = self._load()
    
    def _deep_merge(self, base, override):
        """Deep merge two dictionaries"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                base[key] = self._deep_merge(base[key], value)
            else:
                base[key] = value
        return base
    
    def _smart_merge(self, base, override):
        """
        Smart merge that preserves user's model pricing list.
        - Merges structure from base (prices.default, thresholds, etc.)
        - Does NOT merge base's prices.models - uses only user's models
        """
        # Start with a shallow copy of base
        result = base.copy()
        
        # Explicitly copy nested dictionaries that we might modify to avoid sharing with 'base'
        if 'prices' in result and isinstance(result['prices'], dict):
            result['prices'] = result['prices'].copy()
            if 'default' in result['prices'] and isinstance(result['prices']['default'], dict):
                result['prices']['default'] = result['prices']['default'].copy()
        
        if 'thresholds' in result and isinstance(result['thresholds'], dict):
            result['thresholds'] = result['thresholds'].copy()

        for key, value in override.items():
            if key == 'prices' and isinstance(value, dict):
                # Handle prices specially: merge default pricing, but replace models entirely
                if 'prices' not in result:
                    result['prices'] = {}
                
                # Merge default pricing structure
                if 'default' in value:
                    result['prices']['default'] = value['default']
                
                # Replace models entirely with user's models (don't merge with DEFAULT_SETTINGS models)
                if 'models' in value:
                    result['prices']['models'] = value['models']
                else:
                    # If user has no models, use empty dict (don't inherit DEFAULT_SETTINGS models)
                    result['prices']['models'] = {}
                
                # Preserve any other pricing fields
                for pk, pv in value.items():
                    if pk not in ['default', 'models']:
                        result['prices'][pk] = pv
                        
            elif key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Recursively merge other nested dicts
                result[key] = self._deep_merge(result[key], value)
            else:
                # Simple override
                result[key] = value
        
        return result

    def _normalize_model_settings(self):
        """Normalize model settings and remove redundant overrides"""
        changed = False
        prices = self.settings.setdefault('prices', {})
        models = prices.get('models') if isinstance(prices.get('models'), dict) else {}
        prices['models'] = models

        deleted_models = prices.get('deleted_models')
        if not isinstance(deleted_models, list):
            deleted_models = []
            changed = True
        deleted_models = [m for m in deleted_models if isinstance(m, str)]

        known_default_models = prices.get('known_default_models')
        if not isinstance(known_default_models, list):
            known_default_models = []
            changed = True
        known_default_models = [m for m in known_default_models if isinstance(m, str)]

        default_models = DEFAULT_SETTINGS['prices']['models']
        if not known_default_models:
            if models:
                known_default_models = [m for m in models.keys() if m in default_models]
            else:
                known_default_models = list(default_models.keys())
            changed = True
        to_remove = []
        for model_id, user_price in models.items():
            if model_id in default_models:
                if model_id in deleted_models:
                    to_remove.append(model_id)
                    continue
                if self._prices_match_default(user_price, default_models[model_id]):
                    to_remove.append(model_id)

        for model_id in to_remove:
            del models[model_id]
            changed = True

        prices['models'] = models
        prices['deleted_models'] = list(dict.fromkeys(deleted_models))
        prices['known_default_models'] = list(dict.fromkeys(known_default_models))
        return changed

    def _prices_match_default(self, user_price, default_price):
        """Check if user pricing matches default pricing (price fields only)"""
        for key in ['input', 'output', 'caching', 'request']:
            if float(user_price.get(key, 0.0)) != float(default_price.get(key, 0.0)):
                return False
        return True
    
    def save(self):
        """Save settings to file"""
        os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
        with open(SETTINGS_PATH, 'w') as f:
            json.dump(self.settings, f, indent=2)
        os.chmod(SETTINGS_PATH, 0o600)
    
    def get(self, key, default=None):
        """Get a setting value"""
        keys = key.split('.')
        val = self.settings
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k)
            else:
                return default
        return val if val is not None else default
    
    def set(self, key, value):
        """Set a setting value"""
        keys = key.split('.')
        val = self.settings
        for k in keys[:-1]:
            if k not in val:
                val[k] = {}
            val = val[k]
        val[keys[-1]] = value
        self.save()
    
    def calculate_cost(self, stats, model_id=None, provider_id=None):
        """Calculate cost from token stats with model-specific pricing"""
        if not stats:
            return 0.0

        # Try to get model-specific pricing
        prices = None
        price_source = "unknown"
        
        if model_id and provider_id:
            # Try provider/model format first (most specific)
            combined_key = f"{provider_id}/{model_id}"
            # Use direct dict access to avoid splitting by '/' in settings.get()
            models_dict = self.settings.get('prices', {}).get('models', {})
            prices = models_dict.get(combined_key)
            if prices:
                price_source = f"user_models:{combined_key}"

        if not prices and model_id:
            # Try just model_id
            models_dict = self.settings.get('prices', {}).get('models', {})
            prices = models_dict.get(model_id)
            if prices:
                price_source = f"user_models:{model_id}"

        if not prices and model_id:
            default_models = DEFAULT_SETTINGS['prices']['models']
            if provider_id:
                combined_key = f"{provider_id}/{model_id}"
                prices = default_models.get(combined_key)
                if prices:
                    price_source = f"default_models:{combined_key}"
            if not prices:
                prices = default_models.get(model_id)
                if prices:
                    price_source = f"default_models:{model_id}"

        # Fall back to provider-level defaults if no model match
        if not prices and provider_id:
            if provider_id == 'opencode':
                # OpenCode models are always FREE
                prices = {'input': 0.0, 'output': 0.0, 'caching': 0.0, 'request': 0.0}
                price_source = "provider_default:opencode"
            elif provider_id == 'github-copilot':
                # GitHub Copilot models are token-free, but may have per-request fees
                # Try to find a representative request fee from defaults if possible
                default_models = DEFAULT_SETTINGS['prices']['models']
                # Search for any copilot model to get the standard request fee if not found
                req_fee = 0.0
                for k, v in default_models.items():
                    if k.startswith('github-copilot/'):
                        req_fee = v.get('request', 0.0)
                        break
                prices = {'input': 0.0, 'output': 0.0, 'caching': 0.0, 'request': req_fee}
                price_source = "provider_default:github-copilot"
            elif provider_id == 'nvidia':
                # NVIDIA NIMs are currently mostly free/trial
                prices = {'input': 0.0, 'output': 0.0, 'caching': 0.0, 'request': 0.0}
                price_source = "provider_default:nvidia"

        # Fall back to default prices
        if not prices:
            prices = self.get('prices.default')
            if prices:
                price_source = "prices.default"
            
        if not prices:
            # Hardcoded fallback
            prices = {
                'input': 0.5,
                'output': 3.0,
                'caching': 0.05,
                'request': 0.0
            }
            price_source = "hardcoded_fallback"

        input_tokens = stats.get('input', 0)
        output_tokens = stats.get('output', 0)
        reasoning_tokens = stats.get('reasoning', 0)
        cache_read = stats.get('cache_read', 0)
        cache_write = stats.get('cache_write', 0)
        requests = stats.get('requests', 0)

        total_output = output_tokens + reasoning_tokens
        total_caching = cache_read + cache_write

        cost = (
            (input_tokens * prices.get('input', 0) / 1_000_000) +
            (total_output * prices.get('output', 0) / 1_000_000) +
            (total_caching * prices.get('caching', 0) / 1_000_000) +
            (requests * prices.get('request', 0))
        )

        return cost
    
    def calculate_total_cost(self, model_stats_dict):
        """
        Calculate total cost from a nested model stats dictionary:
        { provider_id: { model_id: stats_dict } }
        """
        if not model_stats_dict:
            return 0.0
            
        total_cost = 0.0
        for provider_id, models in model_stats_dict.items():
            for model_id, stats in models.items():
                total_cost += self.calculate_cost(
                    stats, 
                    model_id=model_id, 
                    provider_id=provider_id
                )
        return total_cost
    
    def add_model_price(self, model_id, prices):
        """Add or update model-specific pricing"""
        if 'models' not in self.settings['prices']:
            self.settings['prices']['models'] = {}
        default_models = DEFAULT_SETTINGS['prices']['models']
        if model_id in default_models and self._prices_match_default(prices, default_models[model_id]):
            if model_id in self.settings['prices']['models']:
                del self.settings['prices']['models'][model_id]
            self._remove_deleted_model(model_id)
            self.save()
            return

        self.settings['prices']['models'][model_id] = prices
        self._remove_deleted_model(model_id)
        self.save()
    
    def get_model_price(self, model_id):
        """Get pricing for a specific model"""
        return self.get(f'prices.models.{model_id}')
    
    def delete_model_price(self, model_id):
        """Delete model-specific pricing"""
        if 'models' in self.settings['prices'] and model_id in self.settings['prices']['models']:
            del self.settings['prices']['models'][model_id]
            self.save()

    def mark_model_deleted(self, model_id):
        """Hide a default model from lists by marking it as deleted"""
        default_models = DEFAULT_SETTINGS['prices']['models']
        if model_id not in default_models:
            return False

        if 'models' in self.settings['prices'] and model_id in self.settings['prices']['models']:
            del self.settings['prices']['models'][model_id]

        deleted_models = self.settings['prices'].setdefault('deleted_models', [])
        if model_id not in deleted_models:
            deleted_models.append(model_id)
        self.save()
        return True

    def _remove_deleted_model(self, model_id):
        deleted_models = self.settings.get('prices', {}).get('deleted_models', [])
        if model_id in deleted_models:
            deleted_models.remove(model_id)
            return True
        return False
    
    def get_version(self):
        """Get current settings version"""
        return self.settings.get('version', '1.0.0')
    
    def get_app_version(self):
        """Get app default version"""
        return DEFAULT_SETTINGS.get('version', '1.0.0')
    
    def check_version_update(self):
        """
        Check if app version differs from settings version.
        Returns: (needs_update, current_version, app_version, new_models, customized_models)
        """
        current_version = self.get_version()
        app_version = self.get_app_version()
        
        if current_version == app_version:
            return False, current_version, app_version, [], []
        
        # Version changed, check for new models
        default_models = DEFAULT_SETTINGS['prices']['models']
        user_models = self.settings.get('prices', {}).get('models', {})
        deleted_models = set(self.settings.get('prices', {}).get('deleted_models', []))
        known_default_models = set(self.settings.get('prices', {}).get('known_default_models', []))
        
        # Find new models (in default but not in user settings)
        new_models = []
        for model_id in default_models:
            if model_id not in known_default_models and model_id not in deleted_models:
                new_models.append(model_id)
        
        # Find customized models (user price differs from default)
        customized_models = []
        for model_id, user_price in user_models.items():
            if model_id in default_models:
                default_price = default_models[model_id]
                if not self._prices_match_default(user_price, default_price):
                    customized_models.append(model_id)
        
        return True, current_version, app_version, new_models, customized_models
    
    def add_new_models(self):
        """
        Identify new models from defaults without overwriting existing ones.
        Returns list of added model IDs.
        """
        default_models = DEFAULT_SETTINGS['prices']['models']
        deleted_models = set(self.settings.get('prices', {}).get('deleted_models', []))
        known_default_models = set(self.settings.get('prices', {}).get('known_default_models', []))
        
        added = []
        for model_id, default_price in default_models.items():
            if model_id not in known_default_models and model_id not in deleted_models:
                added.append(model_id)

        return added
    
    def update_version(self):
        """Update settings version to match app version"""
        self.settings['version'] = self.get_app_version()
        self.settings['prices']['known_default_models'] = list(DEFAULT_SETTINGS['prices']['models'].keys())
        self.save()
    
    def reset_model_to_default(self, model_id):
        """Reset a specific model to default pricing"""
        default_models = DEFAULT_SETTINGS['prices']['models']
        if model_id in default_models:
            if 'models' in self.settings['prices'] and model_id in self.settings['prices']['models']:
                del self.settings['prices']['models'][model_id]
            self._remove_deleted_model(model_id)
            self.save()
            return True
        return False
    
    def reset_all_models_to_default(self):
        """Reset all models to default pricing"""
        self.settings['prices']['models'] = {}
        self.settings['prices']['deleted_models'] = []
        self.save()
