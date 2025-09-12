from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class SerpRequest(BaseModel):
    """Request model for SERP API calls"""
    query: str = Field(..., description="Search query")
    num_results: int = Field(default=10, description="Number of results to return")
    language: str = Field(default="en", description="Search language")
    country: str = Field(default="us", description="Search country")
    engine: str = Field(default="google", description="Search engine")
    date_filter: Optional[str] = Field(None, description="Date filter (d, w, m, y)")
    start_date: Optional[str] = Field(None, description="Start date (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="End date (YYYY-MM-DD)")


class SerpResult(BaseModel):
    """Individual search result from SERP API"""
    title: str = Field(..., description="Result title")
    url: str = Field(..., description="Result URL")
    snippet: str = Field(..., description="Result snippet/description")
    position: int = Field(..., description="Result position in search")
    domain: str = Field(default="", description="Domain of the result")


class SerpResponse(BaseModel):
    """Response model for SERP API calls"""
    request_id: str = Field(..., description="Unique request identifier")
    query: str = Field(..., description="Original search query")
    total_results: int = Field(default=0, description="Total number of results found")
    results: List[SerpResult] = Field(default_factory=list, description="List of search results")
    search_metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional search metadata")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        } 