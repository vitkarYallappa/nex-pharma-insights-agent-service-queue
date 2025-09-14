from typing import Dict, Any
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ImplicationPromptConfig:
    """Configuration for implication generation prompts"""
    
    # Development prompt - more detailed and structured
    DEVELOPMENT_PROMPT = """
System Role:  
You are a Senior Pharmaceutical Content Designer and CDMO market intelligence expert.  
Your responsibility is to transform structured pharmaceutical market data into clear, professional HTML content suitable for internal reports, dashboards, or executive summaries.  
You understand pharma market trends, CDMO operations, biologics manufacturing, and competitive dynamics.  
Your outputs should be precise, structured, and ready for direct use in reports, with a focus on clarity, readability, and semantic HTML structure.

Task:  
From the provided JSON input, generate a clean, semantic HTML snippet that communicates **key actionable implications** derived from the summary.  
Specifically, the HTML must include:  
1. A main heading “Implications”.  
2. Exactly 2 actionable implications as bullet points (<li>), each 1–2 sentences, derived directly from the input.  
The HTML should be fully self-contained, using only semantic tags: <div>, <section>, <h2>, <ul>, <li>.  

Rules:  
1. Output HTML only — no extra text, explanations, or JSON.  
2. Do not include classes, IDs, or CSS.  
3. Keep the structure clean and readable.  
4. Replace placeholders with actual implications derived from the JSON input.  
5. Extract the key actionable points from the input and place them into the bullet points, even if the input is a single paragraph.  

Input Example: 
{{SUMMARY_PLACEHOLDER}}

Expected Output (HTML):  
<div>
  <h2>Implications</h2>
  <ul>
    <li>[Implication 1 derived from the summary]</li>
    <li>[Implication 2 derived from the summary]</li>
  </ul>
</div>
.
"""

    # Production prompt - more concise and focused
    PRODUCTION_PROMPT = """
As a strategic business analyst, analyze these market insights and provide actionable strategic implications for pharmaceutical companies.

**MARKET INSIGHTS:**
{content}

**PROVIDE STRATEGIC IMPLICATIONS:**

## Executive Summary
Key strategic priorities and immediate actions

## Business Strategy Implications
- Market positioning opportunities
- Competitive strategies
- Partnership opportunities

## Operational Implications  
- Resource allocation priorities
- Process improvements
- Technology needs

## Financial Implications
- Investment opportunities
- Cost optimization
- Revenue strategies

## Regulatory Implications
- Compliance requirements
- Risk mitigation

## Strategic Recommendations
- Short-term actions (0-12 months)
- Long-term strategy (1-3 years)

Focus on specific, measurable, and actionable recommendations.
"""


class ImplicationPromptManager:
    """Manager for implication prompt templates and processing"""
    
    def __init__(self, environment: str = "development"):
        self.environment = environment.lower()
        self.config = ImplicationPromptConfig()
        
        logger.info(f"Initialized ImplicationPromptManager for {self.environment} environment")
    
    def get_prompt_template(self) -> str:
        """Get the appropriate prompt template based on environment"""
        if self.environment == "production":
            return self.config.PRODUCTION_PROMPT
        else:
            return self.config.DEVELOPMENT_PROMPT
    
    def format_prompt(self, content: str, metadata: Dict[str, Any] = None) -> str:
        """Format the prompt with content and metadata"""
        try:
            template = self.get_prompt_template()
            
            # Basic content formatting
            formatted_prompt = template.format(content=content)

            formatted_prompt = formatted_prompt.replace('{{SUMMARY_PLACEHOLDER}}', content)

            # Add metadata context if available
            if metadata:
                context_info = self._format_metadata_context(metadata)
                if context_info:
                    formatted_prompt = f"{context_info}\n\n{formatted_prompt}"
            
            logger.info(f"Formatted implication prompt: {len(formatted_prompt)} characters")
            return formatted_prompt
            
        except Exception as e:
            logger.error(f"Error formatting implication prompt: {e}")
            # Fallback to simple format
            return f"Analyze these market insights and provide strategic implications:\n\n{content}"
    
    def _format_metadata_context(self, metadata: Dict[str, Any]) -> str:
        """Format metadata into context information"""
        context_parts = []
        
        if metadata.get('content_type'):
            context_parts.append(f"Content Type: {metadata['content_type']}")
        
        if metadata.get('source'):
            context_parts.append(f"Source: {metadata['source']}")
        
        if metadata.get('industry_focus'):
            context_parts.append(f"Industry Focus: {metadata['industry_focus']}")
        
        if metadata.get('geographic_region'):
            context_parts.append(f"Geographic Region: {metadata['geographic_region']}")
        
        if metadata.get('time_horizon'):
            context_parts.append(f"Time Horizon: {metadata['time_horizon']}")
        
        if context_parts:
            return "**CONTEXT INFORMATION:**\n" + "\n".join(f"- {part}" for part in context_parts)
        
        return ""
    
    def validate_content(self, content: str) -> bool:
        """Validate content before processing"""
        if not content or not content.strip():
            logger.error("Content is empty or whitespace only")
            return False
        
        if len(content) < 50:
            logger.warning(f"Content is very short ({len(content)} characters)")
            return False
        
        if len(content) > 100000:  # 100KB limit
            logger.warning(f"Content is very long ({len(content)} characters)")
            # Still valid, but will be truncated later
        
        return True
    
    def get_environment_info(self) -> Dict[str, Any]:
        """Get information about current environment configuration"""
        return {
            "environment": self.environment,
            "prompt_template": "production" if self.environment == "production" else "development",
            "template_length": len(self.get_prompt_template()),
            "supports_metadata": True
        } 