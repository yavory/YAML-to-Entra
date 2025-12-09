from typing import List, Optional
from pydantic import BaseModel, Field
import yaml

class Metadata(BaseModel):
    name: str
    environment: str
    description: Optional[str] = None

class Certificate(BaseModel):
    type: str
    value: Optional[str] = None

class Claim(BaseModel):
    name: str
    source: str

class GroupAssignment(BaseModel):
    groupId: str
    role: Optional[str] = None

class Spec(BaseModel):
    entityId: str
    assertionConsumerServiceUrl: str
    singleLogoutServiceUrl: Optional[str] = None
    nameIdFormat: Optional[str] = None
    signatureAlgorithm: Optional[str] = None
    certificate: Optional[Certificate] = None
    claims: List[Claim] = Field(default_factory=list)
    groupAssignments: List[GroupAssignment] = Field(default_factory=list)

class SAMLServiceProvider(BaseModel):
    apiVersion: str
    kind: str
    metadata: Metadata
    spec: Spec

def load_config(file_path: str) -> List[SAMLServiceProvider]:
    """
    Parses one or more YAML documents from the file.
    Returns a list of SAMLServiceProvider objects.
    """
    with open(file_path, 'r') as f:
        # load_all returns a generator
        data_gen = yaml.safe_load_all(f)
        configs = []
        for data in data_gen:
            if data is None: 
                continue
            if data.get('kind') == 'SAMLServiceProvider':
                configs.append(SAMLServiceProvider(**data))
    return configs
