from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class C4PersonSchema(BaseModel):
    id: str
    name: str
    description: str
    external: bool = False


class C4SystemSchema(BaseModel):
    id: str
    name: str
    description: str
    external: bool = False


class C4ComponentSchema(BaseModel):
    id: str
    name: str
    container_id: str
    technology: str
    description: str
    source_path: str
    symbol_count: int = 0
    file_count: int = 0
    dependencies: List[str] = Field(default_factory=list)


class C4ContainerSchema(BaseModel):
    id: str
    name: str
    technology: str
    description: str
    container_type: str
    path: Optional[str] = None
    components: List[C4ComponentSchema] = Field(default_factory=list)


class C4RelationshipSchema(BaseModel):
    source_id: str
    target_id: str
    description: str
    technology: Optional[str] = None
    relationship_type: str = "uses"


class C4DiagramsSchema(BaseModel):
    context_mermaid: str
    container_mermaid: str
    component_mermaid: str
    flowchart_mermaid: str


class C4ArchitectureExportResponse(BaseModel):
    repository_id: uuid.UUID
    system_name: str
    system_description: str
    persons: List[C4PersonSchema] = Field(default_factory=list)
    systems: List[C4SystemSchema] = Field(default_factory=list)
    containers: List[C4ContainerSchema] = Field(default_factory=list)
    components: List[C4ComponentSchema] = Field(default_factory=list)
    relationships: List[C4RelationshipSchema] = Field(default_factory=list)
    constraints: List[Dict[str, Any]] = Field(default_factory=list)
    diagrams: C4DiagramsSchema
    markdown_export: str
