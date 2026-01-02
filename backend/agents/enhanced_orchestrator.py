import google.generativeai as genai
from typing import Dict, Any, List, Optional, Union
import os
import re
import json
import time
from datetime import datetime
import hashlib
import base64


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

class EnhancedGeminiAgent:
    def __init__(self, name: str, capabilities: List[str], system_prompt: str, orchestrator: Optional['EnhancedGeminiOrchestrator'] = None):
        self.name = name
        self.capabilities = capabilities
        self.system_prompt = system_prompt
        self.orchestrator = orchestrator
        self.processing_status = "idle"
        
        
        try:
            if GEMINI_API_KEY:
                self.model = genai.GenerativeModel('gemini-2.0-flash-lite')
            else:
                self.model = None
                print(f"Warning: No Gemini API key found for {name}")
        except Exception as e:
            print(f"Gemini initialization error for {name}: {e}")
            self.model = None
    
    def can_handle(self, task: str, file_content: str = None) -> bool:
        
        task_lower = task.lower()
        
        if file_content:
            if self.name == "data_agent":
                data_indicators = ["csv", "json", "data", "dataset", "analysis", "statistics", "chart"]
                return any(indicator in task_lower for indicator in data_indicators)
            elif self.name == "code_agent":
                code_indicators = ["code", "function", "class", "algorithm", "programming", "script"]
                return any(indicator in task_lower for indicator in code_indicators)
            elif self.name == "nlp_agent":
                text_indicators = ["text", "document", "analyze", "sentiment", "summarize", "content"]
                return any(indicator in task_lower for indicator in text_indicators)
        
        if self.name == "nlp_agent":
            keywords = ["analyze", "sentiment", "summarize", "text", "language", "meaning", "translate", "content", "document"]
            return any(keyword in task_lower for keyword in keywords)
        elif self.name == "code_agent":
            keywords = ["code", "python", "javascript", "function", "programming", "debug", "write", "algorithm", "script"]
            return any(keyword in task_lower for keyword in keywords)
        elif self.name == "data_agent":
            keywords = ["data", "analysis", "statistics", "chart", "visualization", "csv", "dataset", "graph"]
            return any(keyword in task_lower for keyword in keywords)
        
        return False
    
    def set_status(self, status: str):
        self.processing_status = status
        if self.orchestrator:
            self.orchestrator.update_agent_status(self.name, status)
    
    def process(self, user_input: str, context: Dict[str, Any] = None, file_content: str = None) -> Dict[str, Any]:
        self.set_status("processing")
        
        try:
            full_context = {
                "user_input": user_input,
                "agent_name": self.name,
                "timestamp": datetime.now().isoformat(),
                "has_file": file_content is not None
            }
            
            if file_content:
                full_context["file_content"] = file_content[:2000]  # Limit for context
            
            if not self.model or not GEMINI_API_KEY:
                response = self._enhanced_fallback_response(user_input, file_content)
            else:
                response = self._generate_gemini_response(user_input, file_content)
            
            self.set_status("idle")
            
            return {
                "success": True,
                "agent": self.name,
                "response": response,
                "metadata": {
                    "model": "gemini-2.0-flash-lite" if self.model else "fallback",
                    "processing_time": time.time(),
                    "context": full_context
                }
            }
            
        except Exception as e:
            self.set_status("error")
            return {
                "success": False,
                "agent": self.name,
                "response": f"I encountered an error while processing your request: {str(e)}",
                "metadata": {"error": str(e), "status": "error"}
            }
    
    def _generate_gemini_response(self, user_input: str, file_content: str = None) -> str:
        """Generate response using Gemini with enhanced prompting"""
        
        enhanced_prompt = f"""
{self.system_prompt}

IMPORTANT FORMATTING GUIDELINES:
- For code: Always use proper markdown formatting with language specification
- Provide clear explanations after code blocks
- Use professional, natural language
- Structure responses with clear sections when appropriate

User Request: {user_input}
"""
        
        if file_content:
            enhanced_prompt += f"\nFile Content (first 2000 chars):\n{file_content[:2000]}"
        
        enhanced_prompt += "\n\nProvide a comprehensive, well-formatted response:"
        
        try:
            response = self.model.generate_content(enhanced_prompt)
            return self._format_response(response.text)
        except Exception as e:
            return self._enhanced_fallback_response(user_input, file_content)
    
    def _format_response(self, raw_response: str) -> str:
        """Format response for better presentation"""
        formatted_response = raw_response
        
        code_block_pattern = r'```(\w+)?\n(.*?)\n```'
        
        def add_copy_indicator(match):
            language = match.group(1) or 'text'
            code = match.group(2)
            return f'```{language}\n{code}\n```'
        
        formatted_response = re.sub(code_block_pattern, add_copy_indicator, formatted_response, flags=re.DOTALL)
        
        return formatted_response
    
    def _enhanced_fallback_response(self, user_input: str, file_content: str = None) -> str:
        """Enhanced fallback responses with file support"""
        
        if file_content:
            return self._file_based_fallback(user_input, file_content)
        
        if self.name == "nlp_agent":
            return self._nlp_enhanced_fallback(user_input)
        elif self.name == "code_agent":
            return self._code_enhanced_fallback(user_input)
        elif self.name == "data_agent":
            return self._data_enhanced_fallback(user_input)
        
        return "I'm ready to help! Please provide more specific details about what you need."
    
    def _file_based_fallback(self, user_input: str, file_content: str) -> str:
        """Handle file-based requests with fallback responses"""
        
        content_preview = file_content[:500] if file_content else ""
        
        if self.name == "nlp_agent":
            return f"""## Document Analysis

**File Content Preview:**
```
{content_preview}...
```

**Analysis Capabilities:**
- **Content Summarization**: I can provide concise summaries of key points
- **Sentiment Analysis**: Identify emotional tone and sentiment patterns
- **Theme Extraction**: Find main topics and recurring themes
- **Text Statistics**: Word count, readability metrics, etc.

**What I found:**
Based on the content preview, this appears to be a text document with substantial content. I can help you analyze various aspects of this document.

*Note: Add a Gemini API key for detailed AI-powered analysis.*
"""
        
        elif self.name == "code_agent":
            return f"""## Code Analysis

**File Content Preview:**
```
{content_preview}...
```

**Code Analysis Capabilities:**
- **Code Review**: Identify potential improvements and best practices
- **Bug Detection**: Find potential issues and suggest fixes
- **Documentation**: Generate comments and documentation
- **Optimization**: Suggest performance improvements

**Initial Assessment:**
This appears to be a code file. I can help with analysis, debugging, optimization, and documentation.

*Note: Add a Gemini API key for advanced code analysis and generation.*
"""
        
        else:  # data_agent
            return f"""## Data Analysis

**File Content Preview:**
```
{content_preview}...
```

**Data Analysis Capabilities:**
- **Statistical Analysis**: Descriptive statistics and insights
- **Data Visualization**: Chart and graph recommendations
- **Data Cleaning**: Identify and handle missing/invalid data
- **Pattern Recognition**: Find trends and correlations

**Initial Assessment:**
This appears to be a data file. I can help with analysis, visualization, and insights extraction.

*Note: Add a Gemini API key for detailed data analysis and code generation.*
"""
    
    def _nlp_enhanced_fallback(self, user_input: str) -> str:
        user_lower = user_input.lower()
        
        if "sentiment" in user_lower:
            return self._analyze_sentiment_with_formatting(user_input)
        
        return """## Natural Language Processing Assistant

I'm your **NLP specialist** ready to help with:

### Text Analysis Services
- **Sentiment Analysis** - Determine emotional tone and polarity
- **Content Summarization** - Extract key points and main ideas  
- **Theme Extraction** - Identify recurring topics and patterns
- **Text Classification** - Categorize content by type or topic

### Language Processing
- **Grammar & Style** - Writing improvement suggestions
- **Translation Support** - Language detection and basic translation
- **Content Generation** - Help with writing and content creation

**How to get started:** Simply paste your text or describe what you need analyzed!

*For advanced AI-powered analysis, please configure a Gemini API key.*
"""
    
    def _code_enhanced_fallback(self, user_input: str) -> str:
        user_lower = user_input.lower()
        
        if any(lang in user_lower for lang in ["python", "javascript", "java", "cpp", "c++"]):
            return self._generate_code_example(user_input)
        
        return """## Programming Assistant

I'm your **Code specialist** ready to help with:

### Development Services
- **Code Generation** - Write functions, classes, and complete programs
- **Debugging & Troubleshooting** - Find and fix code issues
- **Code Review** - Best practices and optimization suggestions
- **Algorithm Implementation** - Data structures and algorithms

### Supported Languages
- **Python** - Web development, data science, automation
- **JavaScript** - Frontend, backend, and full-stack development
- **Java** - Enterprise applications and Android development
- **C/C++** - System programming and performance-critical code

### Code Quality
- Documentation and comments
- Error handling and edge cases
- Performance optimization
- Testing strategies

**Example request:** "Write a Python function to calculate fibonacci numbers"

*For advanced code generation and analysis, please configure a Gemini API key.*
"""
    
    def _data_enhanced_fallback(self, user_input: str) -> str:
        """Enhanced data analysis fallback"""
        return """## Data Science Assistant

I'm your **Data specialist** ready to help with:

### Analytics Services
- **Exploratory Data Analysis** - Understand your dataset structure
- **Statistical Analysis** - Descriptive and inferential statistics
- **Data Visualization** - Charts, graphs, and interactive plots
- **Machine Learning** - Model recommendations and implementation

### Data Processing
- **Data Cleaning** - Handle missing values and outliers
- **Feature Engineering** - Create meaningful variables
- **Data Transformation** - Scaling, encoding, and preprocessing
- **Performance Metrics** - Evaluation and validation strategies

### Tools & Libraries
- **Python**: Pandas, NumPy, Scikit-learn, Matplotlib, Seaborn
- **Visualization**: Plotly, Bokeh, D3.js recommendations
- **Statistics**: SciPy, Statsmodels

**Example request:** "Help me analyze sales data and create visualizations"

*For detailed analysis and code generation, please configure a Gemini API key.*
"""
    
    def _analyze_sentiment_with_formatting(self, user_input: str) -> str:
        
        # Extract text to analyze
        quoted_text = re.findall(r'"([^"]*)"', user_input)
        if quoted_text:
            text_to_analyze = quoted_text[0]
        else:
            text_match = re.search(r'(?:text|sentiment)[:\s]+(.+)', user_input, re.IGNORECASE)
            if text_match:
                text_to_analyze = text_match.group(1).strip()
            else:
                text_to_analyze = user_input
        
        positive_words = ["love", "great", "awesome", "amazing", "excellent", "fantastic", "wonderful", "good", "happy", "perfect", "best"]
        negative_words = ["hate", "bad", "terrible", "awful", "horrible", "disgusting", "worst", "dislike", "angry", "disappointed", "poor"]
        
        text_lower = text_to_analyze.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if negative_count > positive_count:
            sentiment = "**Negative** 😔"
            confidence = "High" if negative_count > 1 else "Moderate"
            indicators = [word for word in negative_words if word in text_lower]
        elif positive_count > negative_count:
            sentiment = "**Positive** 😊"
            confidence = "High" if positive_count > 1 else "Moderate"
            indicators = [word for word in positive_words if word in text_lower]
        else:
            sentiment = "**Neutral** 😐"
            confidence = "Moderate"
            indicators = []

        return f"""## Sentiment Analysis Results

### Text Analyzed
> "{text_to_analyze}"

### Analysis Summary
- **Overall Sentiment**: {sentiment}
- **Confidence Level**: {confidence}
- **Key Indicators**: {', '.join(indicators) if indicators else 'Neutral language patterns'}

### Detailed Insights
{self._get_sentiment_explanation(sentiment, indicators, text_to_analyze)}

---
*For more advanced sentiment analysis including context, emotion detection, and intensity scoring, please configure a Gemini API key.*
"""
    
    def _generate_code_example(self, user_input: str) -> str:
        """Generate code examples with proper formatting"""
        
        if "python" in user_input.lower() and "function" in user_input.lower():
            return """## Python Function Example

```python
def add_two_numbers(a, b):
    \"\"\"
    Add two numbers and return the result.
    
    Args:
        a (int|float): First number
        b (int|float): Second number
    
    Returns:
        int|float: Sum of the two numbers
    
    Examples:
        >>> add_two_numbers(5, 3)
        8
        >>> add_two_numbers(2.5, 3.7)
        6.2
    \"\"\"
    try:
        result = a + b
        return result
    except (TypeError, ValueError) as e:
        raise ValueError(f"Cannot add {a} and {b}: {e}")

# Example usage
if __name__ == "__main__":
    # Test the function
    print(add_two_numbers(10, 20))  # Output: 30
    print(add_two_numbers(3.14, 2.86))  # Output: 6.0
```

### Key Features:
- **Type Hints**: Clear parameter and return types
- **Documentation**: Comprehensive docstring with examples
- **Error Handling**: Graceful handling of invalid inputs
- **Testing**: Example usage and test cases

### Best Practices Applied:
1. **Clear naming**: Function name describes exactly what it does
2. **Input validation**: Handles edge cases and errors
3. **Documentation**: Easy to understand and maintain
4. **Examples**: Shows how to use the function

*For more complex code generation and advanced algorithms, please configure a Gemini API key.*
"""
        
        return "I can help you generate code! Please specify the programming language and what you'd like to create."
    
    def _get_sentiment_explanation(self, sentiment: str, indicators: list, text: str) -> str:
        """Generate detailed sentiment explanation"""
        if "Positive" in sentiment:
            return f"The text expresses **positive sentiment** through words like '{', '.join(indicators[:3])}'. This suggests satisfaction, approval, or positive emotional response. The overall tone indicates a favorable opinion or experience."
        elif "Negative" in sentiment:
            return f"The text shows **negative sentiment** with words like '{', '.join(indicators[:3])}'. This indicates dissatisfaction, criticism, or negative emotional response. The language suggests unfavorable opinions or experiences."
        else:
            return "The text appears **neutral** with balanced or factual language. No strong emotional indicators were detected in either direction, suggesting objective or informational content."

class EnhancedGeminiOrchestrator:
    def __init__(self):
        self.agent_status = {}
        
        # Initialize enhanced agents
        self.agents = {
            "nlp": EnhancedGeminiAgent(
                name="nlp_agent",
                capabilities=["text_analysis", "sentiment_analysis", "summarization", "content_review"],
                system_prompt="""You are an expert Natural Language Processing specialist. Your role is to analyze text, provide sentiment analysis, create summaries, and offer linguistic insights. 

RESPONSE GUIDELINES:
- Use clear, professional language
- Structure responses with headers and sections
- Provide actionable insights
- Include confidence levels when appropriate
- Format code examples with proper markdown

Focus on accuracy, clarity, and practical value in your analysis.""",
                orchestrator=self
            ),
            "code": EnhancedGeminiAgent(
                name="code_agent",
                capabilities=["code_generation", "debugging", "code_review", "algorithm_design"],
                system_prompt="""You are an expert Software Developer and Programming Assistant. Your role is to write clean, efficient code, debug issues, and provide technical guidance.

RESPONSE GUIDELINES:
- Always use proper markdown formatting for code blocks
- Include language specification (```python, ```javascript, etc.)
- Provide clear explanations after code examples
- Include error handling and best practices
- Add comments and documentation in code
- Show example usage when appropriate

Focus on writing production-ready, well-documented code with proper error handling.""",
                orchestrator=self
            ),
            "data": EnhancedGeminiAgent(
                name="data_agent",
                capabilities=["data_analysis", "statistics", "visualization", "machine_learning"],
                system_prompt="""You are an expert Data Scientist and Analytics Specialist. Your role is to analyze data, provide statistical insights, and recommend visualization strategies.

RESPONSE GUIDELINES:
- Provide step-by-step analytical approaches
- Include code examples for data processing
- Suggest appropriate visualization techniques
- Explain statistical concepts clearly
- Consider data quality and validation
- Recommend tools and libraries

Focus on practical, actionable data science solutions with robust methodologies to avoid overfitting and ensure good generalization.""",
                orchestrator=self
            )
        }
    
    def update_agent_status(self, agent_name: str, status: str):
        """Update agent status for UI display"""
        self.agent_status[agent_name] = {
            "status": status,
            "timestamp": time.time()
        }
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get comprehensive agent status"""
        api_status = "configured" if GEMINI_API_KEY else "missing"
        
        return {
            "orchestrator_status": "active",
            "api_status": api_status,
            "available_agents": [
                {
                    "name": agent.name,
                    "capabilities": agent.capabilities,
                    "status": agent.processing_status,
                    "last_updated": self.agent_status.get(agent.name, {}).get("timestamp", time.time())
                }
                for agent in self.agents.values()
            ],
            "total_agents": len(self.agents),
            "real_time_status": self.agent_status
        }
    
    def process_request(self, user_input: str, session_id: str = None, file_content: str = None, file_name: str = None) -> Dict[str, Any]:
        """Enhanced request processing with file support"""
        
        try:
            selected_agent = self._route_request(user_input, file_content)

            if selected_agent in self.agents:
                self.agents[selected_agent].set_status("processing")
                
                response = self.agents[selected_agent].process(
                    user_input, 
                    context={"session_id": session_id, "file_name": file_name},
                    file_content=file_content
                )
                
                return {
                    "success": response.get("success", True),
                    "final_response": response.get("response", "No response generated"),
                    "agent_responses": [response],
                    "metadata": {
                        "selected_agent": selected_agent,
                        "agents_consulted": [selected_agent],
                        "routing_decision": {"selected": selected_agent, "confidence": 0.9},
                        "file_processed": file_content is not None,
                        "processing_time": time.time(),
                        "agent_status": self.get_agent_status()
                    }
                }
            else:
                return {
                    "success": False,
                    "final_response": "Unable to route your request. Please try rephrasing your question.",
                    "metadata": {"error": "routing_failed"}
                }
                
        except Exception as e:
            for agent in self.agents.values():
                agent.set_status("idle")
                
            return {
                "success": False,
                "final_response": f"I encountered an error while processing your request. Please try again. Error: {str(e)}",
                "metadata": {"error": str(e), "timestamp": time.time()}
            }
    
    def _route_request(self, user_input: str, file_content: str = None) -> str:
        """Enhanced routing with file content analysis"""
        user_lower = user_input.lower()

        if file_content:
            content_lower = file_content.lower()

            if any(pattern in content_lower for pattern in [",", "csv", "json", "data", "dataset"]):
                if any(keyword in user_lower for keyword in ["analyze", "data", "statistics", "chart", "visualization"]):
                    return "data"

            if any(pattern in content_lower for pattern in ["def ", "function", "class ", "import", "from "]):
                return "code"

            return "nlp"

        scores = {}
        for agent_name, agent in self.agents.items():
            if agent.can_handle(user_input, file_content):
                scores[agent_name] = self._calculate_enhanced_score(user_input, agent_name)

        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]
        else:
            return "nlp"  
    
    def _calculate_enhanced_score(self, user_input: str, agent_name: str) -> float:
        """Enhanced scoring algorithm for better routing"""
        user_lower = user_input.lower()
        base_score = 0.0
        
        if agent_name == "nlp":
            keywords = {
                "high": ["sentiment", "analyze", "summarize", "text", "content", "document"],
                "medium": ["language", "meaning", "review", "translate", "writing"],
                "low": ["read", "understand", "explain"]
            }
        elif agent_name == "code":
            keywords = {
                "high": ["code", "function", "programming", "debug", "algorithm"],
                "medium": ["python", "javascript", "write", "create", "develop"],
                "low": ["script", "program", "software"]
            }
        elif agent_name == "data":
            keywords = {
                "high": ["data", "analysis", "statistics", "visualization", "chart"],
                "medium": ["dataset", "graph", "plot", "csv", "numbers"],
                "low": ["information", "calculate", "math"]
            }
        else:
            return 0.0
        
        for word in keywords["high"]:
            if word in user_lower:
                base_score += 0.3
        
        for word in keywords["medium"]:
            if word in user_lower:
                base_score += 0.2
        
        for word in keywords["low"]:
            if word in user_lower:
                base_score += 0.1
        
        return base_score