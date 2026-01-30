"""
Configuration module for Antigravity backend.
Loads settings from environment variables with sensible defaults.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""
    
    # Telegram Bot Token
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    WEBAPP_URL: str = os.getenv("WEBAPP_URL", "https://saterlix.github.io/Digi_bot")
    
    # Pricing Configuration
    EXCHANGE_RATE: float = float(os.getenv("EXCHANGE_RATE", "0.92"))
    MARGIN_PERCENT: float = float(os.getenv("MARGIN_PERCENT", "1.05"))
    MARGIN_FIXED: int = int(os.getenv("MARGIN_FIXED", "500"))
    
    # Server Configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8080"))
    
    # Database Configuration
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "antigravity.db")
    
    @classmethod
    def validate(cls) -> list[str]:
        """
        Validate that all required configuration values are set.
        Returns a list of missing configuration keys.
        """
        errors = []
        
        if not cls.DIGIFLAZZ_USER:
            errors.append("DIGIFLAZZ_USER is required")
        if not cls.DIGIFLAZZ_KEY:
            errors.append("DIGIFLAZZ_KEY is required")
        if not cls.BOT_TOKEN:
            errors.append("BOT_TOKEN is required")
            
        return errors
    
    @classmethod
    def is_valid(cls) -> bool:
        """Check if all required configuration values are set."""
        return len(cls.validate()) == 0


# Create a singleton config instance
config = Config()
