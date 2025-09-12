import json
import re
from typing import Dict, Any, Optional, Union
from datetime import datetime

from app.utils.logger import get_logger

logger = get_logger(__name__)


class PerplexityJSONFormatter:
    """
    Handles JSON formatting and parsing for Perplexity API responses.
    Supports both structured JSON responses and fallback text parsing.
    """
    
    @staticmethod
    def parse_response_content(content: str) -> Dict[str, Any]:
        """
        Parse Perplexity response content, handling both JSON and text formats.
        
        Args:
            content: Raw content from Perplexity API response
            
        Returns:
            Structured dictionary with parsed data
        """
        try:
            # First, try to parse as JSON
            json_data = PerplexityJSONFormatter._extract_and_parse_json(content)
            if json_data:
                logger.info("Successfully parsed JSON response from Perplexity")
                return PerplexityJSONFormatter._normalize_json_response(json_data)
            
            # Fallback to text parsing
            logger.info("JSON parsing failed, falling back to text parsing")
            return PerplexityJSONFormatter._parse_text_response(content)
            
        except Exception as e:
            logger.error(f"Error parsing Perplexity response: {str(e)}")
            return PerplexityJSONFormatter._create_error_response(content, str(e))
    
    @staticmethod
    def _extract_and_parse_json(content: str) -> Optional[Dict[str, Any]]:
        """Extract and parse JSON from response content"""
        try:
            # Clean the content first
            cleaned_content = content.strip()
            
            # Try direct JSON parsing
            if cleaned_content.startswith('{') and cleaned_content.endswith('}'):
                return json.loads(cleaned_content)
            
            # Look for JSON block in markdown code blocks
            json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
            json_match = re.search(json_pattern, cleaned_content, re.DOTALL | re.IGNORECASE)
            if json_match:
                return json.loads(json_match.group(1))
            
            # Look for JSON object anywhere in the text
            json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
            json_matches = re.findall(json_pattern, cleaned_content, re.DOTALL)
            
            for match in json_matches:
                try:
                    parsed = json.loads(match)
                    if isinstance(parsed, dict) and len(parsed) > 2:  # Reasonable JSON object
                        return parsed
                except json.JSONDecodeError:
                    continue
            
            return None
            
        except Exception as e:
            logger.warning(f"JSON extraction failed: {str(e)}")
            return None
    
    @staticmethod
    def _normalize_json_response(json_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize JSON response to standard format"""
        try:
            # Expected fields from development prompt
            normalized = {
                "response_type": "json",
                "url": json_data.get("url", ""),
                "title": json_data.get("title", ""),
                "publish_date": json_data.get("publish_date"),
                "source_type": json_data.get("source_type"),
                "main_topic": json_data.get("main_topic", ""),
                "key_points": json_data.get("key_points", []),
                "raw_content": json.dumps(json_data, indent=2),
                "parsed_successfully": True,
                "processing_metadata": {
                    "parsed_at": datetime.utcnow().isoformat(),
                    "parser": "PerplexityJSONFormatter",
                    "fields_found": list(json_data.keys()),
                    "total_fields": len(json_data)
                }
            }
            
            # Validate key_points is a list
            if not isinstance(normalized["key_points"], list):
                normalized["key_points"] = []
            
            # Clean null values
            if normalized["publish_date"] in ["null", "None", ""]:
                normalized["publish_date"] = None
            
            if normalized["source_type"] in ["null", "None", ""]:
                normalized["source_type"] = None
            
            return normalized
            
        except Exception as e:
            logger.error(f"Error normalizing JSON response: {str(e)}")
            return PerplexityJSONFormatter._create_error_response(str(json_data), str(e))
    
    @staticmethod
    def _parse_text_response(content: str) -> Dict[str, Any]:
        """Parse non-JSON text response using pattern matching"""
        try:
            parsed_data = {
                "response_type": "text",
                "url": "",
                "title": "",
                "publish_date": None,
                "source_type": None,
                "main_topic": "",
                "key_points": [],
                "raw_content": content,
                "parsed_successfully": True,
                "processing_metadata": {
                    "parsed_at": datetime.utcnow().isoformat(),
                    "parser": "PerplexityJSONFormatter",
                    "parsing_method": "text_extraction"
                }
            }
            
            # Extract title (usually first line or after "Title:")
            title_patterns = [
                r"Title:\s*(.+)",
                r"^(.+)$"  # First line as fallback
            ]
            
            for pattern in title_patterns:
                match = re.search(pattern, content, re.MULTILINE | re.IGNORECASE)
                if match:
                    parsed_data["title"] = match.group(1).strip()
                    break
            
            # Extract main topic (look for summary or main content)
            topic_patterns = [
                r"Main Topic:\s*(.+)",
                r"Summary:\s*(.+)",
                r"Topic:\s*(.+)"
            ]
            
            for pattern in topic_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    parsed_data["main_topic"] = match.group(1).strip()
                    break
            
            # If no specific topic found, use first paragraph
            if not parsed_data["main_topic"]:
                paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
                if paragraphs:
                    parsed_data["main_topic"] = paragraphs[0][:200] + ("..." if len(paragraphs[0]) > 200 else "")
            
            # Extract key points (numbered lists, bullet points)
            key_points = []
            lines = content.split('\n')
            
            for line in lines:
                line = line.strip()
                # Look for various bullet/number formats
                if (re.match(r'^\d+\.', line) or 
                    line.startswith(('- ', '* ', '• ', '→ ', '▪ '))):
                    # Clean the bullet/number prefix
                    clean_point = re.sub(r'^\d+\.\s*|^[-*•→▪]\s*', '', line).strip()
                    if clean_point and len(clean_point) > 10:  # Meaningful content
                        key_points.append(clean_point)
            
            parsed_data["key_points"] = key_points[:5]  # Limit to 5 points
            
            return parsed_data
            
        except Exception as e:
            logger.error(f"Error parsing text response: {str(e)}")
            return PerplexityJSONFormatter._create_error_response(content, str(e))
    
    @staticmethod
    def _create_error_response(content: str, error_msg: str) -> Dict[str, Any]:
        """Create standardized error response"""
        return {
            "response_type": "error",
            "url": "",
            "title": "Parsing Error",
            "publish_date": None,
            "source_type": None,
            "main_topic": f"Error parsing response: {error_msg}",
            "key_points": [],
            "raw_content": content,
            "parsed_successfully": False,
            "processing_metadata": {
                "parsed_at": datetime.utcnow().isoformat(),
                "parser": "PerplexityJSONFormatter",
                "error": error_msg,
                "parsing_method": "error_fallback"
            }
        }
    
    @staticmethod
    def format_for_downstream(parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format parsed data for downstream processing (insight/implication queues).
        Returns structured data with HTML formatted main_content.
        """
        try:
            if parsed_data.get("response_type") == "json":
                # Create HTML formatted main content
                html_parts = []
                
                # Add title as main heading
                if parsed_data.get("title"):
                    html_parts.append(f"<p><strong>{parsed_data['title']}</strong></p>")
                
                # Add main topic content
                if parsed_data.get("main_topic"):
                    html_parts.append(f"<p>{parsed_data['main_topic']}</p>")
                
                # Add key points as emphasized paragraphs
                if parsed_data.get("key_points"):
                    for point in parsed_data["key_points"]:
                        html_parts.append(f"<p><em>{point}</em></p>")
                
                main_content = "<div>" + "".join(html_parts) + "</div>"
                
                return {
                    "main_content": main_content,
                    "publish_date": parsed_data.get("publish_date"),
                    "source_category": parsed_data.get("source_type")  # Map source_type to source_category
                }
            
            else:
                # For text responses, wrap raw content in HTML
                raw_content = parsed_data.get("raw_content", "")
                main_content = f"<div><p>{raw_content}</p></div>"
                
                return {
                    "main_content": main_content,
                    "publish_date": None,
                    "source_category": None
                }
                
        except Exception as e:
            logger.error(f"Error formatting for downstream: {str(e)}")
            error_content = f"<div><p>Error formatting response: {str(e)}</p></div>"
            return {
                "main_content": error_content,
                "publish_date": None,
                "source_type": None
            }
    
    @staticmethod
    def extract_metadata(parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata for database storage"""
        return {
            "response_type": parsed_data.get("response_type", "unknown"),
            "parsed_successfully": parsed_data.get("parsed_successfully", False),
            "has_structured_data": parsed_data.get("response_type") == "json",
            "key_points_count": len(parsed_data.get("key_points", [])),
            "has_publish_date": parsed_data.get("publish_date") is not None,
            "has_source_type": parsed_data.get("source_type") is not None,
            "processing_metadata": parsed_data.get("processing_metadata", {}),
            "content_length": len(parsed_data.get("raw_content", "")),
            "title_length": len(parsed_data.get("title", "")),
            "topic_length": len(parsed_data.get("main_topic", ""))
        } 