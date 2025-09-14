"""
Simple prompt configuration for Perplexity content analysis
Just 2 prompts: development and production
"""
import os

class SimplePromptConfig:
    """Simple prompt configuration with just 2 options"""
    
    # Development prompt - simple and quick for testing
    DEVELOPMENT_PROMPT = """
  System Role:  
You are a Senior Pharmaceutical Intelligence Analyst.  
Your responsibility is to analyze pharma-related online content (from the provided URL only) and produce a structured JSON output. You must follow strict rules, ensure factual accuracy, and write expanded but precise summaries for internal pharma teams.  

Task:  
Fetch and analyze the content from the provided URL. Summarize it into structured, factual, and domain-relevant insights.  

Inputs:  
- URL: {{URL_PLACEHOLDER}}  
- Title: {{TITLE_PLACEHOLDER}}  

Strict Rules:  
1. Use only the content from the provided URL.  
2. Do not infer, assume, or add knowledge beyond the page.  
3. If publish_date is not explicitly available → return null.  
4. If source_category cannot be identified → return null.  
5. Always return all keys in the JSON, even if values are null.  
6. main_topic must be a short paragraph (3–5 sentences) summarizing the central theme with context and implications.  
7. key_points must include 5–8 concise but detailed, pharma-relevant points.  
8. Output only JSON — no extra text, notes, or commentary.  


Output Format (JSON):  
{
  "url": "{{URL_PLACEHOLDER}}",
  "title": "{{TITLE_PLACEHOLDER}}",
  "publish_date": "YYYY-MM-DD or null",
  "source_category": "regulatory | clinical_trials | scientific_journal | news_media | corporate | market_research | policy | other | null",
  "main_topic": "Expanded summary in 3–5 sentences covering the event, significance, and implications.",
  "key_points": [
    "Detailed point 1",
    "Detailed point 2",
    "Detailed point 3",
    "Detailed point 4",
    "Detailed point 5",
    "Optional point 6",
    "Optional point 7",
    "Optional point 8"
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