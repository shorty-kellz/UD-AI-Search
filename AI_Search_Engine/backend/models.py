"""
Simplified Pydantic models for data validation and serialization
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date, datetime

class ContentBase(BaseModel):
    """Base content model with common fields"""
    title: str = Field(..., description="Full title of the article")
    summary: Optional[str] = Field(None, description="Rich summary or description")
    source: str = Field(..., description="Source type: 'Fast Fact', 'UD Content', etc.")
    category: Optional[str] = Field(None, description="High-level grouping")
    sub_category: Optional[str] = Field(None, description="Sub-grouping under category")
    tags: Optional[List[str]] = Field(None, description="List of tags")
    FF_tags: Optional[List[str]] = Field(None, description="FastFact parsed tags from PDF articles")
    auto_category: Optional[str] = Field(None, description="Auto-generated category")
    auto_sub_category: Optional[str] = Field(None, description="Auto-generated sub-category")
    auto_tags: Optional[List[str]] = Field(None, description="Auto-generated tags")
    labels_approved: bool = Field(default=False, description="Whether labels have been approved")
    url: Optional[str] = Field(None, description="Link to external source")

class ContentCreate(ContentBase):
    """Model for creating new content"""
    id: str = Field(..., description="Unique identifier e.g., 'FF365'")
    last_edited: Optional[date] = Field(None, description="Timestamp of most recent edit")
    status: str = Field(default="active", description="Status: 'active', 'archived'")
    version: str = Field(default="1.0", description="Version tracking")

class Content(ContentBase):
    """Complete content model with all fields"""
    id: str
    last_edited: Optional[date] = None
    status: str = "active"
    version: str = "1.0"

    class Config:
        from_attributes = True

class TaxonomyEntry(BaseModel):
    id: Optional[int] = None
    domain: str
    category: str
    sub_category: Optional[str] = None
    last_edited: Optional[datetime] = None
    status: str = "active"
