from typing import Dict, Any, Optional
from datetime import datetime
from .models import ExtractedContent
from ...shared.utils.logger import get_logger

logger = get_logger(__name__)

class PerplexityResponseHandler:
    """Process and validate Perplexity API responses for single URLs"""
    
    @staticmethod
    def process_single_response(response: Dict[str, Any], url: str) -> Optional[ExtractedContent]:
        """Process single extraction response"""
        try:
            choices = response.get("choices", [])
            if not choices:
                return None
            
            message = choices[0].get("message", {})
            content = message.get("content", "")
            
            if not content or len(content.strip()) < 50:
                return None
            
            # Parse structured content
            parsed = PerplexityResponseHandler._parse_content_structure(content)
            
            return ExtractedContent(
                url=url,
                title=parsed["title"],
                content=parsed["summary"],
                metadata=PerplexityResponseHandler._extract_content_metadata(response),
                author=parsed.get("author"),
                published_date=parsed.get("published_date"),
                word_count=len(parsed["summary"].split()),
                language=parsed.get("language", "en"),
                content_type=parsed.get("content_type", "article"),
                extraction_confidence=PerplexityResponseHandler._calculate_quality_score(parsed, response)
            )
            
        except Exception as e:
            logger.warning(f"Single response processing error: {str(e)}")
            return None
    
    @staticmethod
    def _parse_content_structure(content: str) -> Dict[str, Any]:
        """Parse structured content from extraction"""
        lines = content.strip().split('\n')
        
        # Extract title (usually first line)
        title = lines[0].strip() if lines else "Untitled"
        title = PerplexityResponseHandler._clean_title(title)
        
        # Extract summary (remaining content)
        summary_lines = lines[1:] if len(lines) > 1 else [content]
        summary = '\n'.join(summary_lines).strip()
        
        # Try to extract metadata from structured content
        metadata = PerplexityResponseHandler._extract_inline_metadata(content)
        
        return {
            "title": title,
            "summary": summary,
            "author": metadata.get("author"),
            "published_date": metadata.get("published_date"),
            "language": metadata.get("language", "en"),
            "content_type": metadata.get("content_type", "article")
        }
    
    @staticmethod
    def _clean_title(title: str) -> str:
        """Clean and normalize title"""
        # Remove common markdown/formatting
        prefixes = ["# ", "## ", "### ", "Title:", "TITLE:"]
        for prefix in prefixes:
            if title.upper().startswith(prefix.upper()):
                title = title[len(prefix):].strip()
        
        # Remove quotes
        if title.startswith('"') and title.endswith('"'):
            title = title[1:-1]
        
        return title[:200]  # Limit length
    
    @staticmethod
    def _extract_inline_metadata(content: str) -> Dict[str, Any]:
        """Extract metadata from content text"""
        metadata = {}
        
        # Look for author patterns
        import re
        author_patterns = [
            r"Author:\s*(.+)",
            r"By\s+(.+)",
            r"Written by\s+(.+)"
        ]
        
        for pattern in author_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                metadata["author"] = match.group(1).strip()
                break
        
        # Look for date patterns
        date_patterns = [
            r"Published:\s*(.+)",
            r"Date:\s*(.+)",
            r"(\d{4}-\d{2}-\d{2})"
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, content)
            if match:
                try:
                    date_str = match.group(1).strip()
                    # Try to parse date (simplified)
                    if len(date_str) == 10 and date_str.count('-') == 2:
                        metadata["published_date"] = datetime.fromisoformat(date_str)
                except:
                    pass
        
        return metadata
    
    @staticmethod
    def _calculate_quality_score(parsed: Dict[str, Any], response: Dict[str, Any]) -> float:
        """Calculate content quality score"""
        score = 0.0
        
        # Title quality
        title = parsed.get("title", "")
        if title and title != "Untitled":
            score += 0.2
            if len(title) > 20:
                score += 0.1
        
        # Content length
        summary = parsed.get("summary", "")
        word_count = len(summary.split())
        if word_count >= 100:
            score += 0.3
        elif word_count >= 50:
            score += 0.2
        elif word_count >= 20:
            score += 0.1
        
        # Metadata presence
        if parsed.get("author"):
            score += 0.1
        if parsed.get("published_date"):
            score += 0.1
        
        # Response quality indicators
        usage = response.get("usage", {})
        if usage.get("total_tokens", 0) > 500:
            score += 0.1
        
        citations = response.get("citations", [])
        if citations:
            score += min(len(citations) * 0.05, 0.2)
        
        return min(score, 1.0)
    
    @staticmethod
    def _extract_content_metadata(response: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata from API response"""
        return {
            "usage": response.get("usage", {}),
            "citations": response.get("citations", []),
            "model": response.get("model", ""),
            "extraction_timestamp": datetime.utcnow().isoformat(),
            "response_id": response.get("id", "")
        }
