"""
Prompt configuration for Relevance Check using simple analysis
Development and production prompts for content relevance analysis
"""
import os

class RelevanceCheckPromptConfig:
    """Prompt configuration for relevance check generation"""
    
    # Development prompt - simple and quick for testing
    DEVELOPMENT_PROMPT = """
    Check relevance of this research data:
    
    URL: {url}
    Title: {title}
    User Query: {user_prompt}
    
    Research Data:
    {perplexity_response}
    
    Please provide:
    1. Is this content relevant? (Yes/No)
    2. Relevance score (0-100)
    3. Key relevance indicators (2-3 points)
    
    Keep it concise for development testing.
    """
    
    # Production prompt - comprehensive for real analysis
    PRODUCTION_PROMPT = """
    Based on the following pharmaceutical/healthcare research data, check content relevance:

    **SOURCE INFORMATION:**
    - URL: {url}
    - Title: {title}
    - Original Query: {user_prompt}
    - Content ID: {content_id}

    **RESEARCH DATA:**
    {perplexity_response}

    **REQUIRED RELEVANCE ANALYSIS:**

    1. **Content Relevance Assessment**
       - Is this content relevant to pharmaceutical market intelligence?
       - Does it align with the user's query?
       - Quality and depth of information provided

    2. **Relevance Score (0-100)**
       - Pharmaceutical industry relevance
       - Market intelligence value
       - Query alignment score

    3. **Key Relevance Indicators**
       - Specific pharmaceutical terms found
       - Market intelligence elements
       - Regulatory or competitive information

    **FORMAT REQUIREMENTS:**
    - Provide clear Yes/No relevance decision
    - Include numerical relevance score (0-100)
    - List specific relevance indicators
    - Focus on pharmaceutical/healthcare market intelligence value

    Generate clear relevance assessment for content filtering.
    """

class RelevanceCheckPromptManager:
    """Prompt manager for relevance check with development and production modes"""
    
    @staticmethod
    def get_prompt(perplexity_response: str, url_data: dict, user_prompt: str = "", 
                   content_id: str = "", mode: str = None) -> str:
        """Get the appropriate relevance check prompt based on mode"""
        
        # Determine mode: check environment or use parameter
        if mode is None:
            mode = os.getenv('RELEVANCE_CHECK_MODE', 'development').lower()
        
        # Extract data from url_data
        url = url_data.get('url', 'No URL provided')
        title = url_data.get('title', 'No title available')
        
        # Choose prompt based on mode
        if mode == 'production':
            prompt_template = RelevanceCheckPromptConfig.PRODUCTION_PROMPT
        else:
            prompt_template = RelevanceCheckPromptConfig.DEVELOPMENT_PROMPT
        
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
        """Set the relevance check prompt mode (for runtime changes)"""
        if mode.lower() in ['development', 'production']:
            os.environ['RELEVANCE_CHECK_MODE'] = mode.lower()
            return True
        return False
    
    @staticmethod
    def get_current_mode() -> str:
        """Get current prompt mode"""
        return os.getenv('RELEVANCE_CHECK_MODE', 'development').lower() 