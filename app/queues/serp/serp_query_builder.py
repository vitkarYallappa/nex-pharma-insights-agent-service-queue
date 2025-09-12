"""
SERP Query Builder
Simple utility to build Google search queries for SERP API calls
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta


def build_query(keywords: List[str], sources: List[Dict[str, Any]] = None, 
                date_filter: str = None, additional_terms: str = None) -> Dict[str, Any]:
    """
    Build a Google search query for SERP API
    
    Args:
        keywords: List of keywords to search for (e.g., ["Obesity", "Weight loss"])
        sources: List of source dictionaries with 'url' field
        date_filter: Date filter ('d', 'w', 'm', 'y' or custom date range)
        additional_terms: Additional search terms to include
    
    Returns:
        Dictionary with query and SERP API parameters
    """
    # Build the main query with OR logic for keywords
    if not keywords:
        raise ValueError("Keywords list cannot be empty")
    
    # Create OR query for keywords in the format ("keyword1" OR "keyword2")
    keyword_query = " OR ".join([f'"{keyword}"' for keyword in keywords])
    
    # Add site restrictions if sources provided
    site_query = ""
    if sources:
        sites = []
        for source in sources:
            if 'url' in source:
                # Extract domain from URL
                domain = source['url'].replace('https://', '').replace('http://', '').rstrip('/')
                sites.append(f"site:{domain}")
        
        if sites:
            site_query = f" ({' OR '.join(sites)})"
    
    # Combine query parts in the format ("keywords") (site:domain.com)
    full_query = f"({keyword_query}){site_query}"
    
    # Add additional terms if provided
    if additional_terms:
        full_query += f" {additional_terms}"
    
    # Build SERP API parameters
    params = {
        "q": full_query,
        "engine": "google",
        "num": 5,
        "hl": "en",
        "gl": "us",
        "output": "json"
    }
    
    # Add date filter if specified
    if date_filter:
        if date_filter in ['d', 'w', 'm', 'y']:
            params["tbs"] = f"qdr:{date_filter}"
        else:
            # Custom date format handling
            params["tbs"] = date_filter
    
    return {
        "query": full_query,
        "params": params,
        "keywords": keywords,
        "sources": sources or [],
        "date_filter": date_filter
    }


def build_date_range_query(keywords: List[str], sources: List[Dict[str, Any]] = None,
                          start_date: str = None, end_date: str = None) -> Dict[str, Any]:
    """
    Build query with custom date range
    
    Args:
        keywords: List of keywords
        sources: List of source dictionaries
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
    
    Returns:
        Query dictionary with date range filter
    """
    # Build base query
    query_data = build_query(keywords, sources)
    
    # Add custom date range
    if start_date or end_date:
        date_filter = "cdr:1"
        
        if start_date:
            # Convert YYYY-MM-DD to M/DD/YYYY
            start_formatted = _format_date_for_google(start_date)
            date_filter += f",cd_min:{start_formatted}"
        
        if end_date:
            end_formatted = _format_date_for_google(end_date)
            date_filter += f",cd_max:{end_formatted}"
        
        query_data["params"]["tbs"] = date_filter
        query_data["date_filter"] = f"{start_date} to {end_date}"
    
    return query_data


def _format_date_for_google(date_str: str) -> str:
    """Convert YYYY-MM-DD to M/DD/YYYY format for Google"""
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        month = str(date_obj.month)  # No leading zero
        day = str(date_obj.day).zfill(2)  # Leading zero for day
        year = str(date_obj.year)
        return f"{month}/{day}/{year}"
    except Exception:
        return date_str


# Example usage and test function
if __name__ == "__main__":
    # Default parameters as specified
    default_keywords = [
        "Obesity",
        "Weight loss", 
        "Overweight",
        "Obese"
    ]
    
    default_sources = [
        {
            "name": "ClinicalTrials",
            "type": "clinical", 
            "url": "https://clinicaltrials.gov/"
        },
        {
            "name": "Reuters Business",
            "type": "news",
            "url": "https://www.reuters.com/business"
        }
    ]
    
    print("=== SERP Query Builder Examples ===")
    
    # Example 1: Basic query
    query1 = build_query(default_keywords, default_sources)
    print(f"\n1. Basic Query:")
    print(f"   Query: {query1['query']}")
    print(f"   Params: {query1['params']}")
    
    # Example 2: Query with date filter
    query2 = build_query(default_keywords, default_sources, date_filter="m")
    print(f"\n2. Query with Date Filter (Past Month):")
    print(f"   Query: {query2['query']}")
    print(f"   Date Filter: {query2['params'].get('tbs', 'None')}")
    
    # Example 3: Query with custom date range
    query3 = build_date_range_query(
        default_keywords, 
        default_sources,
        start_date="2024-01-01",
        end_date="2024-12-31"
    )
    print(f"\n3. Query with Date Range:")
    print(f"   Query: {query3['query']}")
    print(f"   Date Range: {query3['date_filter']}")
    print(f"   TBS: {query3['params'].get('tbs', 'None')}")
    
    # Example 4: Query with additional terms
    query4 = build_query(
        default_keywords,
        default_sources, 
        additional_terms="FDA approval pharmaceutical"
    )
    print(f"\n4. Query with Additional Terms:")
    print(f"   Query: {query4['query']}") 