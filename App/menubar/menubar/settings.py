"""
Settings management for OpenCode Token Meter
"""
import json
import os
import shutil

OLD_SETTINGS_PATH = os.path.join(
    os.path.expanduser("~"),
    "Library/Application Support/OpenCode Token Meter/settings.json"
)

SETTINGS_PATH = os.path.join(
    os.path.expanduser("~"),
    "Library/Application Support/OpenCode Token Meter/settings.json"
)

DEFAULT_SETTINGS = {
    "prices": {
        "default": {
            "input": 0.5,      # $ per 1M tokens (Gemini 3 Flash default)
            "output": 3.0,     # $ per 1M tokens
            "caching": 0.05,   # $ per 1M tokens (read + write)
            "request": 0.0     # $ per request
        },
        "models": {
            # GitHub Copilot - Claude Sonnet 4.5 (free tokens, $0.04 per request)
            "github-copilot/claude-sonnet-4.5": {
                "input": 0.0,
                "output": 0.0,
                "caching": 0.0,
                "request": 0.04,
                "provider": "github-copilot"
            },
            # GitHub Copilot - Claude Opus 4.5 (free tokens, $0.04 per request)
            "github-copilot/claude-opus-4.5": {
                "input": 0.0,
                "output": 0.0,
                "caching": 0.0,
                "request": 0.04,
                "provider": "github-copilot"
            },
            # GitHub Copilot - GPT-5 Mini (free tokens, $0.04 per request)
            "github-copilot/gpt-5-mini": {
                "input": 0.0,
                "output": 0.0,
                "caching": 0.0,
                "request": 0.04,
                "provider": "github-copilot"
            },
            # GitHub Copilot - GPT-5.2 Codex (free tokens, $0.04 per request)
            "github-copilot/gpt-5.2-codex": {
                "input": 0.0,
                "output": 0.0,
                "caching": 0.0,
                "request": 0.04,
                "provider": "github-copilot"
            },
            # GitHub Copilot - Gemini 3 Flash ($0.0132 per request)
            "github-copilot/gemini-3-flash-preview": {
                "input": 0.0,
                "output": 0.0,
                "caching": 0.0,
                "request": 0.0132,
                "provider": "github-copilot"
            },
            # GitHub Copilot - Gemini 3 Pro ($0.04 per request)
            "github-copilot/gemini-3-pro": {
                "input": 0.0,
                "output": 0.0,
                "caching": 0.0,
                "request": 0.04,
                "provider": "github-copilot"
            },
            # Google - Gemini 3 Flash (token pricing)
            "google/gemini-3-flash-preview": {
                "input": 0.5,
                "output": 3.0,
                "caching": 0.05,
                "request": 0.0,
                "provider": "google"
            },
            # Google - Gemini 3 Pro (5x Flash pricing)
            "google/gemini-3-pro": {
                "input": 2.5,
                "output": 15.0,
                "caching": 0.25,
                "request": 0.0,
                "provider": "google"
            },
            # NVIDIA - All models are FREE
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
            "nvidia/z-ai/glm-4.7": {
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
            # OpenCode - All models are FREE
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
            "opencode/minimax-m2.1-free": {
                "input": 0.0,
                "output": 0.0,
                "caching": 0.0,
                "request": 0.0,
                "provider": "opencode"
            }
        }
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
                    result = self._smart_merge(DEFAULT_SETTINGS.copy(), loaded)
                    return result
            except:
                pass
        return DEFAULT_SETTINGS.copy()
    
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
        result = base.copy()
        
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
        if model_id and provider_id:
            # Try provider/model format first (most specific)
            combined_key = f"{provider_id}/{model_id}"
            # Use direct dict access to avoid splitting by '/' in settings.get()
            models_dict = self.settings.get('prices', {}).get('models', {})
            prices = models_dict.get(combined_key)
        
        if not prices and model_id:
            # Try just model_id
            models_dict = self.settings.get('prices', {}).get('models', {})
            prices = models_dict.get(model_id)
        
        # Fall back to default prices
        if not prices:
            prices = self.get('prices.default')
            if not prices:
                # Hardcoded fallback
                prices = {
                    'input': 0.5,
                    'output': 3.0,
                    'caching': 0.05,
                    'request': 0.0
                }
        
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
    
    def add_model_price(self, model_id, prices):
        """Add or update model-specific pricing"""
        if 'models' not in self.settings['prices']:
            self.settings['prices']['models'] = {}
        self.settings['prices']['models'][model_id] = prices
        self.save()
    
    def get_model_price(self, model_id):
        """Get pricing for a specific model"""
        return self.get(f'prices.models.{model_id}')
    
    def delete_model_price(self, model_id):
        """Delete model-specific pricing"""
        if 'models' in self.settings['prices'] and model_id in self.settings['prices']['models']:
            del self.settings['prices']['models'][model_id]
            self.save()
