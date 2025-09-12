import asyncio
import aiohttp
import os
from typing import Dict, Any, Optional, List
from .models import SerpRequest, SerpResponse, SerpResult
from .serp_query_builder import build_query, build_date_range_query
from config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
"""
async with SerpAPI() as serp_api:
    result = await serp_api.search_with_date_range(
        keywords=["Obesity", "Weight loss", "Overweight", "Obese"],
        source={
            "name": "ClinicalTrials",
            "type": "clinical", 
            "url": "https://clinicaltrials.gov/"
        },
        start_date="2024-08-08",
        end_date="2024-08-10"
    )
    """
class SerpAPI:
    """Real SERP API client for web search with improved error handling and structure"""
    
    def __init__(self):
        # Multiple fallback strategies to get API key
        self.api_key = self._get_api_key()
        self.base_url = "https://serpapi.com/search"
        self.session = None
        
        # Debug logging for API key
        if not self.api_key:
            logger.error("SERP_API_KEY is not set in any source")
            logger.error(f"Settings SERP_API_KEY: {getattr(settings, 'SERP_API_KEY', 'ATTR_NOT_FOUND')}")
            logger.error(f"Environment SERP_API_KEY: {os.getenv('SERP_API_KEY', 'ENV_NOT_FOUND')}")
            logger.error(f"Direct .env file check: {self._check_env_file()}")
            raise ValueError("SERP_API_KEY is required but not found in settings or environment")
        else:
            logger.info(f"SERP API initialized with key: {self.api_key[:10]}...")  # Show first 10 chars for debugging
    
    def _get_api_key(self) -> Optional[str]:
        """Try multiple methods to get the API key"""
        # Method 1: From settings
        try:
            if hasattr(settings, 'SERP_API_KEY') and settings.SERP_API_KEY:
                logger.debug("API key found in settings")
                return settings.SERP_API_KEY
        except Exception as e:
            logger.warning(f"Failed to get API key from settings: {e}")
        
        # Method 2: From environment variable
        env_key = os.getenv('SERP_API_KEY')
        if env_key:
            logger.debug("API key found in environment")
            return env_key
        
        # Method 3: Try to load from .env file directly
        env_file_key = self._load_from_env_file()
        if env_file_key:
            logger.debug("API key found in .env file")
            return env_file_key
        
        return None
    
    def _load_from_env_file(self) -> Optional[str]:
        """Load API key directly from .env file as fallback"""
        try:
            import os
            from pathlib import Path
            
            # Look for .env file in current directory and parent directories
            current_dir = Path.cwd()
            for path in [current_dir, current_dir.parent, current_dir.parent.parent]:
                env_file = path / '.env'
                if env_file.exists():
                    logger.debug(f"Found .env file at: {env_file}")
                    with open(env_file, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith('SERP_API_KEY='):
                                key = line.split('=', 1)[1].strip()
                                if key:
                                    return key
            return None
        except Exception as e:
            logger.warning(f"Failed to load from .env file: {e}")
            return None
    
    def _check_env_file(self) -> str:
        """Check if .env file exists and contains SERP_API_KEY"""
        try:
            from pathlib import Path
            current_dir = Path.cwd()
            for path in [current_dir, current_dir.parent, current_dir.parent.parent]:
                env_file = path / '.env'
                if env_file.exists():
                    with open(env_file, 'r') as f:
                        content = f.read()
                        if 'SERP_API_KEY=' in content:
                            return f"Found in {env_file}"
            return "Not found in any .env file"
        except Exception as e:
            return f"Error checking .env file: {e}"
    
    async def __aenter__(self):
        # Create session with proper timeout and headers
        timeout = aiohttp.ClientTimeout(total=60)
        self.session = aiohttp.ClientSession(timeout=timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def build_serp_url(self, keywords: List[str], source: Dict[str, Any] = None, 
                      date_filter: str = "cdr:1", additional_terms: str = None) -> str:
        """
        Build complete SERP API URL in the format:
        https://serpapi.com/search.json?engine=google&q=("keyword") (site:domain.com)&tbs=cdr:1&api_key=xxx
        
        Args:
            keywords: List of keywords
            source: Single source dictionary with 'url' field
            date_filter: Date filter (default: "cdr:1" for custom date range)
            additional_terms: Additional search terms
            
        Returns:
            Complete SERP API URL string
        """
        try:
            # Convert single source to list for query builder
            sources = [source] if source else None
            
            # Build the query using query builder
            query_data = build_query(keywords, sources, date_filter, additional_terms)
            
            # Build URL parameters
            params = {
                "engine": "google",
                "q": query_data['query'],
                "tbs": date_filter,
                "api_key": self.api_key
            }
            
            # Build complete URL
            import urllib.parse
            query_string = urllib.parse.urlencode(params)
            complete_url = f"{self.base_url}.json?{query_string}"
            
            logger.info(f"Generated SERP URL: {complete_url}")
            return complete_url
            
        except Exception as e:
            logger.error(f"URL building failed: {str(e)}")
            raise Exception(f"Failed to build SERP URL: {str(e)}")

    async def search_with_query_builder(self, keywords: List[str], source: Dict[str, Any] = None, 
                                       date_filter: str = None, additional_terms: str = None):
        """
        Search using the query builder for optimized queries
        
        Args:
            keywords: List of keywords (e.g., ["Obesity", "Weight loss"])
            source: Single source dictionary with 'url' field
            date_filter: Date filter ('d', 'w', 'm', 'y')
            additional_terms: Additional search terms
            
        Returns:
            SerpResponse with search results
        """
        try:
            # Convert single source to list for query builder
            sources = [source] if source else None
            
            # Build the query using query builder
            query_data = build_query(keywords, sources, date_filter, additional_terms)
            
            # Create SerpRequest from query data
            request = SerpRequest(
                query=query_data['query'],
                num_results=query_data['params']['num'],
                language=query_data['params']['hl'],
                country=query_data['params']['gl'],
                engine=query_data['params']['engine']
            )
            
            # Add date filter if present
            if 'tbs' in query_data['params']:
                # Extract date filter from tbs parameter
                tbs = query_data['params']['tbs']
                if tbs.startswith('qdr:'):
                    request.date_filter = tbs.replace('qdr:', '')
            
            logger.info(f"Searching with built query: {query_data['query']}")
            return await self.search(request)
            
        except Exception as e:
            logger.error(f"Query builder search failed: {str(e)}")
            raise Exception(f"Search with query builder failed: {str(e)}")
    
    async def search_with_date_range(self, keywords: List[str], source: Dict[str, Any] = None,
                                    start_date: str = None, end_date: str = None) -> SerpResponse:
        """
        Search using query builder with custom date range
        
        Args:
            keywords: List of keywords
            source: Single source dictionary with 'url' field
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            SerpResponse with search results
        """
        try:
            # Convert single source to list for query builder
            sources = [source] if source else None
            
            # Build query with date range
            query_data = build_date_range_query(keywords, sources, start_date, end_date)
            
            # Create SerpRequest
            request = SerpRequest(
                query=query_data['query'],
                num_results=query_data['params']['num'],
                language=query_data['params']['hl'],
                country=query_data['params']['gl'],
                engine=query_data['params']['engine'],
                start_date=start_date,
                end_date=end_date
            )
            
            logger.info(f"Searching with date range query: {query_data['query']}")
            return await self.search(request)
            
        except Exception as e:
            logger.error(f"Date range search failed: {str(e)}")
            raise Exception(f"Date range search failed: {str(e)}")
    
    async def search(self, request: SerpRequest) -> SerpResponse:
        """Execute search query using SERP API with improved error handling"""
        try:
            if not self.session:
                timeout = aiohttp.ClientTimeout(total=60)
                self.session = aiohttp.ClientSession(timeout=timeout)
            
            params = self._build_params(request)
            
            # Add proper headers for SerpAPI
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
                "Connection": "keep-alive"
            }
            
            logger.info(f"Making SERP API request for query: {request.query}")
            
            async with self.session.get(
                self.base_url, 
                params=params, 
                headers=headers
            ) as response:
                # Enhanced error handling
                if response.status == 401:
                    raise Exception("Invalid API key or authentication failed")
                elif response.status == 403:
                    raise Exception("API access forbidden - check your subscription")
                elif response.status == 429:
                    raise Exception("Rate limit exceeded - too many requests")
                elif response.status == 500:
                    raise Exception("SerpAPI server error - try again later")
                elif response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"API request failed with status {response.status}: {error_text}")
                
                data = await response.json()
                
                # Check for API-level errors in response
                if "error" in data:
                    raise Exception(f"SerpAPI error: {data['error']}")
                
                return self._parse_response(data, request)
                
        except aiohttp.ClientTimeout:
            logger.error(f"Timeout error for SERP query: {request.query}")
            raise Exception("Request timeout - SerpAPI took too long to respond")
        except aiohttp.ClientError as e:
            logger.error(f"Client error for SERP query {request.query}: {str(e)}")
            raise Exception(f"Network error: {str(e)}")
        except Exception as e:
            logger.error(f"SERP API error for query {request.query}: {str(e)}")
            raise Exception(f"Search failed: {str(e)}")
    
    def _build_params(self, request: SerpRequest) -> Dict[str, Any]:
        """Build search parameters with improved structure"""
        params = {
            "q": request.query,
            "api_key": self.api_key,
            "engine": request.engine,
            "num": request.num_results,
            "hl": request.language,
            "gl": request.country,
            "output": "json"  # Explicitly request JSON format
        }
        
        # Add date filtering if specified
        if request.date_filter:
            # Map common date filters to Google's tbs format
            date_mapping = {
                "d": "qdr:d",  # Past day
                "w": "qdr:w",  # Past week  
                "m": "qdr:m",  # Past month
                "y": "qdr:y"   # Past year
            }
            if request.date_filter in date_mapping:
                params["tbs"] = date_mapping[request.date_filter]
            else:
                params["tbs"] = f"qdr:{request.date_filter}"
                
        elif request.start_date and request.end_date:
            # Custom date range (Google format: M/DD/YYYY)
            start_formatted = self._format_date_for_google(request.start_date)
            end_formatted = self._format_date_for_google(request.end_date)
            params["tbs"] = f"cdr:1,cd_min:{start_formatted},cd_max:{end_formatted}"
            
        elif request.start_date:
            # From start date to now
            from datetime import datetime
            start_formatted = self._format_date_for_google(request.start_date)
            today = self._format_date_for_google(datetime.now().strftime("%Y-%m-%d"))
            params["tbs"] = f"cdr:1,cd_min:{start_formatted},cd_max:{today}"
        
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        
        logger.debug(f"SERP API parameters: {params}")
        return params
    
    def _format_date_for_google(self, date_str: str) -> str:
        """Convert YYYY-MM-DD to M/DD/YYYY format for Google (cross-platform compatible)"""
        try:
            from datetime import datetime
            # Parse YYYY-MM-DD format
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            # Return in M/DD/YYYY format (cross-platform compatible)
            month = str(date_obj.month)  # No leading zero
            day = str(date_obj.day).zfill(2)  # Leading zero for day
            year = str(date_obj.year)
            return f"{month}/{day}/{year}"
        except Exception as e:
            logger.warning(f"Date formatting failed for {date_str}: {str(e)}")
            # If parsing fails, return as-is
            return date_str
    
    def _parse_response(self, data: Dict[str, Any], request: SerpRequest) -> SerpResponse:
        """Parse SERP API response with enhanced field extraction"""
        try:
            # Extract organic results with better error handling
            organic_results = data.get("organic_results", [])
            results = []
            
            for i, result in enumerate(organic_results):
                try:
                    # Handle URL validation more gracefully
                    url = result.get("link", "")
                    if not url:
                        url = result.get("url", "")
                    
                    # Clean and validate URL
                    if url and not url.startswith(('http://', 'https://')):
                        url = f"https://{url}"
                    
                    serp_result = SerpResult(
                        title=result.get("title", ""),
                        url=url,
                        snippet=result.get("snippet", ""),
                        position=i + 1,
                        domain=self._extract_domain(url)
                    )
                    results.append(serp_result)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse result {i}: {str(e)}")
                    # Continue with other results
                    continue
            
            # Extract search metadata with fallbacks
            search_info = data.get("search_information", {})
            search_metadata = data.get("search_metadata", {})
            
            # Combine metadata from different sources
            combined_metadata = {
                **search_metadata,
                "search_information": search_info,
                "serpapi_pagination": data.get("serpapi_pagination", {}),
                "related_searches": data.get("related_searches", []),
                "people_also_ask": data.get("people_also_ask", [])
            }
            
            return SerpResponse(
                request_id=f"serp_{int(asyncio.get_event_loop().time())}_{hash(request.query)}",
                query=request.query,
                total_results=search_info.get("total_results", 0),
                results=results,
                search_metadata=combined_metadata
            )
            
        except Exception as e:
            logger.error(f"Response parsing error for URL {request.query}: {str(e)}")
            # Return minimal response on parsing error
            return SerpResponse(
                request_id=f"serp_error_{int(asyncio.get_event_loop().time())}",
                query=request.query,
                total_results=0,
                results=[],
                search_metadata={"error": str(e), "raw_data_keys": list(data.keys())}
            )
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL with better error handling"""
        try:
            if not url:
                return ""
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc
            # Remove www. prefix if present
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except Exception as e:
            logger.warning(f"Domain extraction failed for {url}: {str(e)}")
            return ""

    # Legacy method for backward compatibility with enhanced error handling
    async def call_api(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Legacy API call method with improved error handling"""
        try:
            # Convert legacy format to new format with validation
            query = data.get("query", "")
            if not query:
                return {
                    "status": "error",
                    "error": "Query parameter is required"
                }
            
            request = SerpRequest(
                query=query,
                num_results=min(data.get("num_results", 10), 100),  # Cap at 100
                language=data.get("language", "en"),
                country=data.get("country", "us"),
                engine=data.get("engine", "google")
            )
            
            response = await self.search(request)
            
            return {
                "status": "success", 
                "data": response.dict(),
                "results_count": len(response.results),
                "total_results": response.total_results
            }
            
        except Exception as e:
            logger.error(f"Legacy API call failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "error_type": type(e).__name__
            }
