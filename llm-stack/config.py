"""
Configuration management for Discord Bot
Loads all environment variables and provides centralized configuration.
"""
import os
from dataclasses import dataclass
from typing import List


@dataclass
class BotConfig:
    """Centralized configuration for Discord bot"""
    
    # Required
    discord_token: str
    
    # LLM Configuration
    openai_api_base: str = "http://litellm:4000/v1"
    openai_api_key: str = "sk-test"
    model_name: str = "qwen-vl"
    
    # Bot Settings
    web_viewer_url: str = "http://192.168.0.88:5050"
    show_thought_process: str = "hidden"  # hidden, spoiler, or block
    
    # Conference Settings
    target_conferences: List[str] = None
    ccf_categories: List[str] = None
    ccf_url_template: str = "https://raw.githubusercontent.com/ccfddl/ccf-deadlines/main/conference/{category}/{id}.yml"
    
    # Discord Settings
    command_prefix: str = "!"
    
    # Report Settings
    reports_dir: str = "/app/reports"
    
    @classmethod
    def from_env(cls) -> "BotConfig":
        """Load configuration from environment variables"""
        discord_token = os.getenv("DISCORD_TOKEN")
        if not discord_token:
            raise ValueError("DISCORD_TOKEN environment variable is required")
        
        # Parse conference lists
        target_conferences = os.getenv(
            "TARGET_CONFERENCES",
            "neurips,icml,iclr,cvpr,iccv,eccv,aaai,ijcai,acl,emnlp,naacl,coling,colm,sigkdd,cikm,recsys,www,sigir,wsdm,icse,fse"
        ).split(",")
        
        ccf_categories = os.getenv("CCF_CATEGORIES", "AI,DM,DB,CN,SE,SC").split(",")
        
        return cls(
            discord_token=discord_token,
            openai_api_base=os.getenv("OPENAI_API_BASE", "http://litellm:4000/v1"),
            openai_api_key=os.getenv("OPENAI_API_KEY", "sk-test"),
            model_name=os.getenv("MODEL_NAME", "qwen-vl"),
            web_viewer_url=os.getenv("WEB_VIEWER_URL", "http://192.168.0.88:5050"),
            show_thought_process=os.getenv("SHOW_THOUGHT_PROCESS", "hidden"),
            target_conferences=[c.strip() for c in target_conferences],
            ccf_categories=[c.strip() for c in ccf_categories],
            command_prefix=os.getenv("COMMAND_PREFIX", "!"),
            reports_dir=os.getenv("REPORTS_DIR", "/app/reports"),
        )
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        if self.show_thought_process not in ["hidden", "spoiler", "block"]:
            raise ValueError(f"Invalid SHOW_THOUGHT_PROCESS: {self.show_thought_process}")
