"""
Prompt configuration for Implication generation using AWS Bedrock
Development and production prompts for business implications analysis
"""
import os

class ImplicationPromptConfig:
    """Prompt configuration for business implications generation"""
    
    # Development prompt - simple and quick for testing
    DEVELOPMENT_PROMPT = """
    Generate business implications from this research data:
    
    URL: {url}
    Title: {title}
    User Query: {user_prompt}
    
    Research Data:
    {perplexity_response}
    
    Please provide:
    1. Strategic impact (1-2 sentences)
    2. Key risks (2-3 bullet points)
    3. Implementation considerations (brief overview)
    
    Keep it concise for development testing.
    """
    
    # Production prompt - comprehensive for real analysis
    PRODUCTION_PROMPT = """
    Based on the following pharmaceutical/healthcare research data, generate comprehensive business implications:

    **SOURCE INFORMATION:**
    - URL: {url}
    - Title: {title}
    - Original Query: {user_prompt}
    - Content ID: {content_id}

    **RESEARCH DATA:**
    {perplexity_response}

    **REQUIRED BUSINESS IMPLICATIONS:**

    1. **Strategic Business Impact**
       - Strategic significance and relevance
       - Impact on business objectives and goals
       - Alignment with corporate strategy
       - Long-term strategic implications

    2. **Operational Considerations**
       - Operational changes required
       - Resource allocation implications
       - Process modifications needed
       - Organizational capability requirements

    3. **Financial Implications**
       - Revenue impact and opportunities
       - Cost implications and investments required
       - ROI projections and financial benefits
       - Budget and funding considerations

    4. **Risk Assessment & Mitigation**
       - Business risks and threats
       - Market risks and uncertainties
       - Regulatory and compliance risks
       - Risk mitigation strategies and contingencies

    5. **Competitive Advantages/Disadvantages**
       - Competitive positioning implications
       - Differentiation opportunities
       - Competitive threats and responses
       - Market positioning strategies

    6. **Implementation Recommendations**
       - Immediate action items and priorities
       - Implementation timeline and milestones
       - Required resources and capabilities
       - Success metrics and KPIs
       - Change management considerations

    **FORMAT REQUIREMENTS:**
    - Provide structured, actionable business implications
    - Use clear headings and bullet points
    - Include specific recommendations and action items
    - Focus on pharmaceutical/healthcare business context
    - Ensure implications are practical and implementable

    Generate comprehensive business implications that enable informed decision-making and strategic planning.
    """

class ImplicationPromptManager:
    """Prompt manager for implication generation with development and production modes"""
    
    @staticmethod
    def get_prompt(perplexity_response: str, url_data: dict, user_prompt: str = "", 
                   content_id: str = "", mode: str = None) -> str:
        """Get the appropriate implication prompt based on mode"""
        
        # Determine mode: check environment or use parameter
        if mode is None:
            mode = os.getenv('IMPLICATION_MODE', 'development').lower()
        
        # Extract data from url_data
        url = url_data.get('url', 'No URL provided')
        title = url_data.get('title', 'No title available')
        
        # Choose prompt based on mode
        if mode == 'production':
            prompt_template = ImplicationPromptConfig.PRODUCTION_PROMPT
        else:
            prompt_template = ImplicationPromptConfig.DEVELOPMENT_PROMPT
        
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
        """Set the implication prompt mode (for runtime changes)"""
        if mode.lower() in ['development', 'production']:
            os.environ['IMPLICATION_MODE'] = mode.lower()
            return True
        return False
    
    @staticmethod
    def get_current_mode() -> str:
        """Get current prompt mode"""
        return os.getenv('IMPLICATION_MODE', 'development').lower() 