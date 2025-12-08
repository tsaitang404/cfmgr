"""Configuration management for Cloudflare Worker."""

import os


class Config:
    """Application configuration."""
    
    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.d1_database_id = os.getenv("D1_DATABASE_ID")
        self.r2_bucket_name = os.getenv("R2_BUCKET_NAME", "cfmgr-bucket")
        self.api_token = os.getenv("CLOUDFLARE_API_TOKEN")
        self.account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")


def get_config() -> Config:
    """Get application configuration.
    
    Returns:
        Config instance
    """
    return Config()
