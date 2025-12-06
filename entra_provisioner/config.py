from typing import List, Optional
from pydantic import BaseModel, Field
import yaml

class EntraAppConfig(BaseModel):
    name: str = Field(..., description="Display name of the application")
    identifier_uris: List[str] = Field(default_factory=list, description="List of Identifier URIs (Entity IDs)")
    reply_urls: List[str] = Field(default_factory=list, description="List of Reply URLs (ACS URLs)")
    logo_url: Optional[str] = Field(None, description="URL of the application logo")
    owners: List[str] = Field(default_factory=list, description="List of owner Object IDs or UPNs")
    
    # SAML specific optional settings
    sign_on_url: Optional[str] = None
    logout_url: Optional[str] = None

class Config(BaseModel):
    applications: List[EntraAppConfig]

def load_config(file_path: str) -> Config:
    with open(file_path, 'r') as f:
        data = yaml.safe_load(f)
    return Config(**data)
