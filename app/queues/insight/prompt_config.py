"""
Prompt configuration for Insight generation using AWS Bedrock
Development and production prompts for market insights analysis
"""
import os

class InsightPromptConfig:
    """Prompt configuration for market insights generation"""
    
    # Development prompt - simple and quick for testing
    DEVELOPMENT_PROMPT = """
    Generate market insights from this research data:
    
    URL: {url}
    Title: {title}
    
    Research Data:
    {perplexity_response}
    
    Please provide:
    1. Key market trend (1-2 sentences)
    2. Main opportunities (2-3 bullet points)
    3. Competitive landscape (brief overview)
    
    
    Please provide the response strictly in the following HTML format:

<div>
  <p><strong>Key market trend:</strong></p>
  <p>[1–2 sentences describing the key market trend]</p>

  <p><strong>Main opportunities:</strong></p>
  <ul>
    <li>[Opportunity 1]</li>
    <li>[Opportunity 2]</li>
    <li>[Opportunity 3]</li>
  </ul>

  <p><strong>Competitive landscape:</strong></p>
  <p>[Brief overview of the competitive landscape]</p>
</div>
    """
    
    # Production prompt - comprehensive for real analysis
    PRODUCTION_PROMPT = """
    Based on the following pharmaceutical/healthcare research data, generate comprehensive market insights:

    **SOURCE INFORMATION:**
    - URL: {url}
    - Title: {title}
    - Original Query: {user_prompt}
    - Content ID: {content_id}

    **RESEARCH DATA:**
    {perplexity_response}

    **REQUIRED MARKET INSIGHTS:**

    1. **Market Trends & Opportunities**
       - Current market dynamics
       - Emerging trends and patterns
       - Growth opportunities and market gaps
       - Future market projections

    2. **Competitive Landscape Analysis**
       - Key market players and positioning
       - Competitive advantages and differentiators
       - Market share dynamics
       - Competitive threats and opportunities

    3. **Regulatory Environment**
       - Current regulatory status
       - Regulatory trends and changes
       - Compliance requirements
       - Regulatory risks and opportunities

    4. **Market Size & Growth Potential**
       - Current market size estimates
       - Growth rate projections
       - Market segmentation insights
       - Revenue potential analysis

    5. **Key Success Factors**
       - Critical success factors for market entry
       - Market barriers and challenges
       - Required capabilities and resources
       - Strategic recommendations

    **FORMAT REQUIREMENTS:**
    - Provide structured, actionable insights
    - Use clear headings and bullet points
    - Include specific data points when available
    - Focus on pharmaceutical/healthcare market intelligence
    - Ensure insights are business-relevant and strategic

    Generate comprehensive market insights that enable strategic decision-making.
    """

class InsightPromptManager:
    """Prompt manager for insight generation with development and production modes"""
    
    @staticmethod
    def get_prompt(perplexity_response: str, url_data: dict, user_prompt: str = "", 
                   content_id: str = "", mode: str = None) -> str:
        """Get the appropriate insight prompt based on mode"""
        
        # Determine mode: check environment or use parameter
        if mode is None:
            mode = os.getenv('INSIGHT_MODE', 'development').lower()
        
        # Extract data from url_data
        url = url_data.get('url', 'No URL provided')
        title = url_data.get('title', 'No title available')
        
        # Choose prompt based on mode
        if mode == 'production':
            prompt_template = InsightPromptConfig.PRODUCTION_PROMPT
        else:
            prompt_template = InsightPromptConfig.DEVELOPMENT_PROMPT
        
        # Format the prompt with actual data
        return prompt_template.format(
            url=url,
            title=title,
            user_prompt=user_prompt or 'No specific query provided',
            content_id=content_id or 'Unknown',
            perplexity_response=perplexity_response or 'No research data available'
        ).strip()
    
    @staticmethod
    def get_available_modes() -> list:
        """Get list of available prompt modes"""
        return ['development', 'production']
    
    @staticmethod
    def set_mode(mode: str) -> bool:
        """Set the insight prompt mode (for runtime changes)"""
        if mode.lower() in ['development', 'production']:
            os.environ['INSIGHT_MODE'] = mode.lower()
            return True
        return False
    
    @staticmethod
    def get_current_mode() -> str:
        """Get current prompt mode"""
        return os.getenv('INSIGHT_MODE', 'development').lower() 