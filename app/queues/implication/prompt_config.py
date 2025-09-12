from typing import Dict, Any
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ImplicationPromptConfig:
    """Configuration for implication generation prompts"""
    
    # Development prompt - more detailed and structured
    DEVELOPMENT_PROMPT = """
You are a strategic business analyst specializing in market implications and strategic planning. 
Analyze the provided market insights and generate comprehensive strategic implications.

**INSTRUCTIONS:**
1. Focus on actionable strategic implications for pharmaceutical and healthcare companies
2. Provide specific, measurable recommendations where possible
3. Consider both short-term tactical and long-term strategic implications
4. Address regulatory, competitive, operational, and financial aspects
5. Use clear, professional business language
6. Structure your response with clear headings and bullet points

**MARKET INSIGHTS TO ANALYZE:**
{content}

**GENERATE STRATEGIC IMPLICATIONS COVERING:**

## Executive Summary
- Key strategic takeaways and priority actions

## Strategic Business Implications
- Market positioning opportunities
- Competitive advantage strategies  
- Partnership and collaboration opportunities
- Market entry/expansion strategies

## Operational Implications
- Resource allocation recommendations
- Process optimization opportunities
- Technology and infrastructure needs
- Organizational capability requirements

## Financial Implications
- Investment priorities and opportunities
- Cost optimization strategies
- Revenue enhancement opportunities
- Risk management considerations

## Regulatory & Compliance Implications
- Regulatory compliance requirements
- Policy change impacts
- Risk mitigation strategies

## Long-term Strategic Recommendations
- 3-5 year strategic priorities
- Innovation and R&D focus areas
- Market positioning strategies
- Competitive differentiation approaches

Provide specific, actionable recommendations that pharmaceutical companies can implement.
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