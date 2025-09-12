"""
Simple prompt configuration for Perplexity content analysis
Just 2 prompts: development and production
"""
import os

class SimplePromptConfig:
    """Simple prompt configuration with just 2 options"""
    
    # Development prompt - simple and quick for testing
    DEVELOPMENT_PROMPT = """
   Task: Analyze the given URL by fetching its full content.  

Inputs:  
- URL: {{URL_PLACEHOLDER}}  
- Title: {{TITLE_PLACEHOLDER}}  

Strict Rules:  
- Only fetch and use the content from the provided URL.  
- Do not use external sources beyond the given URL.  
- Do not infer, assume, or add outside knowledge.  
- If publish date or source_category is missing in the content, return null.  
- Always include all keys in the JSON, even if values are null.  

Allowed Source Categories:  
- "regulatory" (FDA, EMA, MHRA, etc.)  
- "clinical_trials" (ClinicalTrials.gov, trial registries, publications)  
- "scientific_journal" (peer-reviewed research)  
- "news_media" (pharma/healthcare press coverage)  
- "corporate" (company websites, press releases, investor reports)  
- "market_research" (analyst reports, industry insights)  
- "policy" (government/WHO guidelines, health authorities)  
- "other" (anything outside these categories)  

Output Format (JSON):  
{
  "url": "{{URL_PLACEHOLDER}}",
  "title": "{{TITLE_PLACEHOLDER}}",
  "publish_date": "YYYY-MM-DD or null",
  "source_category": "regulatory | clinical_trials | scientific_journal | news_media | corporate | market_research | policy | other | null",
  "main_topic": "1–2 sentences",
  "key_points": [
    "point 1",
    "point 2",
    "point 3"
  ]
}

    """
    
    # Production prompt - comprehensive for real analysis
    PRODUCTION_PROMPT = """
    Analyze this pharmaceutical/healthcare URL for market intelligence:
    
    URL: {{URL_PLACEHOLDER}}
    Title: {{TITLE_PLACEHOLDER}}
    Content Preview: {{SNIPPET_PLACEHOLDER}}
    Keywords: {{KEYWORDS_PLACEHOLDER}}
    
    Please provide a comprehensive analysis with:
    
    1. **Executive Summary** (2-3 sentences)
    2. **Key Findings** (5-7 main points)
    3. **Market Intelligence**:
       - Market trends
       - Competitive insights
       - Regulatory information
    4. **Business Implications**:
       - Opportunities
       - Risks
       - Strategic recommendations
    5. **Data Quality**: Rate the reliability of this source (High/Medium/Low)
    
    Focus on actionable pharmaceutical market intelligence.
    """

class PromptManager:
    """Simple prompt manager with just development and production modes"""
    
    @staticmethod
    def get_prompt(url_data: dict, keywords: list = None, mode: str = None) -> str:
        """Get the appropriate prompt based on mode"""
        
        # Determine mode: check environment or use parameter
        if mode is None:
            mode = os.getenv('PERPLEXITY_MODE', 'development').lower()
        
        # Extract data from url_data
        url = url_data.get('url', 'No URL provided')
        title = url_data.get('title', 'No title available')
        snippet = url_data.get('snippet', 'No content preview available')
        keywords_str = ', '.join(keywords) if keywords else 'None specified'
        
        # Choose prompt based on mode
        if mode == 'production':
            prompt_template = SimplePromptConfig.PRODUCTION_PROMPT
        else:
            prompt_template = SimplePromptConfig.DEVELOPMENT_PROMPT
        
        # Use string replacement instead of .format() to avoid KeyError with URLs containing {}
        try:
            prompt = prompt_template.replace('{{URL_PLACEHOLDER}}', url)
            prompt = prompt.replace('{{TITLE_PLACEHOLDER}}', title)
            prompt = prompt.replace('{{SNIPPET_PLACEHOLDER}}', snippet)
            prompt = prompt.replace('{{KEYWORDS_PLACEHOLDER}}', keywords_str)
            
            return prompt.strip()
        except Exception as e:
            # Log the error and return a fallback prompt
            print(f"Error formatting prompt: {e}")
            fallback_prompt = f"""
            Analyze this pharmaceutical/healthcare URL:
            
            URL: {url}
            Title: {title}
            
            Please provide a comprehensive analysis focusing on pharmaceutical market intelligence.
            """
            return fallback_prompt.strip()
    
    @staticmethod
    def get_available_modes() -> list:
        """Get list of available prompt modes"""
        return ['development', 'production']
    
    @staticmethod
    def set_mode(mode: str) -> bool:
        """Set the prompt mode (for runtime changes)"""
        if mode.lower() in ['development', 'production']:
            os.environ['PERPLEXITY_MODE'] = mode.lower()
            return True
        return False 