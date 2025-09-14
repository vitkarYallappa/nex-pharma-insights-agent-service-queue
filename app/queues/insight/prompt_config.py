"""
Prompt configuration for Insight generation using AWS Bedrock
Development and production prompts for market insights analysis
"""
import os

class InsightPromptConfig:
    """Prompt configuration for market insights generation"""
    
    # Development prompt - simple and quick for testing
    DEVELOPMENT_PROMPT = """
    System Role:  
You are a Senior Pharmaceutical Content Designer and CDMO market intelligence expert.  
Your responsibility is to transform structured pharmaceutical market data into clear, professional HTML content suitable for internal reports, dashboards, or executive summaries.  
You understand pharma market trends, CDMO operations, biologics manufacturing, and competitive dynamics.  
Your outputs should be precise, structured, and ready for direct use in reports, with a focus on clarity, readability, and semantic HTML structure.

Task:  
From the provided JSON input, generate a clean, semantic HTML snippet that communicates key CDMO market insights.  
Specifically, the HTML must include:  
1. Key market trend — summarize the most critical market developments in 1–2 sentences.  
2. Main opportunities — present 3 actionable opportunities as bullet points.  
3. Competitive landscape — summarize the competitive situation in a concise paragraph.  
The HTML should be fully self-contained, using only semantic tags: <div>, <section>, <h2>, <h3>, <p>, <ul>, <li>.  

Rules:  
1. Output HTML only — no extra text, explanations, or JSON.  
2. Do not include classes, IDs, or CSS.  
3. Keep the structure clean and readable.  
4. Replace placeholders with the actual text from the JSON input.  
5. Extract the key points from the input and place them into the appropriate sections, even if the input is a single paragraph.  

Input Example: 
URL: {{URL_PLACEHOLDER}}
Title: {{TITLE_PLACEHOLDER}} 
{{SUMMARY_PLACEHOLDER}}

Expected Output (HTML):  
<div>
  <h2>Market Insight</h2>

  <section>
    <h3>Key market trend</h3>
    <p>The CDMO market is experiencing rapid growth driven by biologics and personalized therapies.</p>
  </section>

  <section>
    <h3>Main opportunities</h3>
    <ul>
      <li>Expansion of mRNA and gene therapy production capabilities</li>
      <li>Strategic partnerships with biotech and pharma companies</li>
      <li>Investment in single-use and modular manufacturing technologies</li>
    </ul>
  </section>

  <section>
    <h3>Competitive landscape</h3>
    <p>Several mid-size CDMOs are entering the biologics space, increasing competition and driving innovation in manufacturing processes.</p>
  </section>
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

        try:
            prompt = prompt_template.replace('{{URL_PLACEHOLDER}}', url)
            prompt = prompt.replace('{{TITLE_PLACEHOLDER}}', title)
            prompt = prompt.replace('{{SUMMARY_PLACEHOLDER}}', perplexity_response)

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
        """Set the insight prompt mode (for runtime changes)"""
        if mode.lower() in ['development', 'production']:
            os.environ['INSIGHT_MODE'] = mode.lower()
            return True
        return False
    
    @staticmethod
    def get_current_mode() -> str:
        """Get current prompt mode"""
        return os.getenv('INSIGHT_MODE', 'development').lower() 