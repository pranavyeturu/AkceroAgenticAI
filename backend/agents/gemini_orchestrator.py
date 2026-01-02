import google.generativeai as genai
from typing import Dict, Any, List, Optional
import os
import re

# Configure Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

class GeminiAgent:
    def __init__(self, name: str, capabilities: List[str], system_prompt: str, orchestrator: Optional['GeminiMultiAgentOrchestrator'] = None):
        self.name = name
        self.capabilities = capabilities
        self.system_prompt = system_prompt
        self.orchestrator = orchestrator

        # Initialize Gemini model
        try:
            if GEMINI_API_KEY:
                self.model = genai.GenerativeModel('gemini-2.0-flash-lite')
            else:
                self.model = None
                print(f"Warning: No Gemini API key found for {name}")
        except Exception as e:
            print(f"Gemini initialization error for {name}: {e}")
            self.model = None
    
    def can_handle(self, task: str) -> bool:
        """Check if agent can handle the task based on keywords"""
        task_lower = task.lower()
        
        if self.name == "nlp_agent":
            keywords = ["analyze", "sentiment", "summarize", "text", "language", "meaning"]
            return any(keyword in task_lower for keyword in keywords)
        elif self.name == "code_agent":
            keywords = ["code", "python", "function", "programming", "debug", "write"]
            return any(keyword in task_lower for keyword in keywords)
        elif self.name == "data_agent":
            keywords = ["data", "analysis", "statistics", "chart", "visualization"]
            return any(keyword in task_lower for keyword in keywords)
        
        return False
    
    def process(self, user_input: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process user input with Gemini"""
        
        # Fallback responses when Gemini is not available
        if not self.model or not GEMINI_API_KEY:
            fallback_responses = {
                "nlp_agent": self._nlp_fallback(user_input),
                "code_agent": self._code_fallback(user_input),
                "data_agent": self._data_fallback(user_input)
            }
            return {
                "success": True,
                "agent": self.name,
                "response": fallback_responses.get(self.name, "I can help you with that, but I need an API key to provide detailed responses."),
                "metadata": {"mode": "fallback", "model": "none"}
            }
        
        try:
            # Combine system prompt with user input
            full_prompt = f"{self.system_prompt}\n\nUser: {user_input}\n\nAssistant:"
            
            response = self.model.generate_content(full_prompt)
            
            return {
                "success": True,
                "agent": self.name,
                "response": response.text,
                "metadata": {"model": "gemini-pro", "mode": "api"}
            }
            
        except Exception as e:
            # Return helpful error message
            return {
                "success": False,
                "agent": self.name,
                "response": f"I encountered an error: {str(e)}. Using fallback response instead.",
                "metadata": {"error": str(e), "mode": "error"}
            }
    
    def _nlp_fallback(self, user_input: str) -> str:
        """Fallback response for NLP tasks"""
        if "sentiment" in user_input.lower():
            return "I can analyze sentiment! For the text you provided, I would typically examine positive/negative indicators, emotional tone, and context clues to determine if the sentiment is positive, negative, or neutral. To get detailed analysis, please add a Gemini API key."
        elif "summarize" in user_input.lower():
            return "I can create summaries! I would identify key points, main themes, and essential information to create a concise summary. For detailed summarization, please add a Gemini API key."
        else:
            return "I'm your NLP specialist! I can help with text analysis, sentiment analysis, summarization, and language processing. Add a Gemini API key for full functionality."
    
    def _code_fallback(self, user_input: str) -> str:
        """Fallback response for coding tasks"""
        if "python" in user_input.lower() and "function" in user_input.lower():
            return """I can help with Python functions! Here's a simple example:

```python
def add_two_numbers(a, b):
    \"\"\"Add two numbers and return the result\"\"\"
    return a + b

# Usage example:
result = add_two_numbers(5, 3)
print(result)  # Output: 8
```

For more complex code generation, please add a Gemini API key."""
        else:
            return "I'm your coding assistant! I can help with code generation, debugging, code review, and programming best practices. Add a Gemini API key for detailed assistance."
    
    def _data_fallback(self, user_input: str) -> str:
        """Fallback response for data tasks"""
        return "I'm your data analysis expert! I can help with data processing, statistical analysis, visualization recommendations, and data insights. Add a Gemini API key for detailed analysis and code examples."

class GeminiMultiAgentOrchestrator:
    def __init__(self):
        # Initialize agents with different specializations
        self.agents = {
            "nlp": GeminiAgent(
                name="nlp_agent",
                capabilities=["text_analysis", "sentiment_analysis", "summarization"],
                system_prompt="You are an expert NLP and text analysis specialist. Provide detailed, accurate analysis of text including sentiment, themes, and insights. Be concise but thorough.",
                orchestrator=self
            ),
            "code": GeminiAgent(
                name="code_agent", 
                capabilities=["code_generation", "debugging", "code_review"],
                system_prompt="You are an expert software developer. Provide working code examples, debug issues, and explain programming concepts clearly. Always include practical, runnable code.",
                orchestrator=self
            ),
            "data": GeminiAgent(
                name="data_agent",
                capabilities=["data_analysis", "statistics", "visualization"],
                system_prompt="You are an expert data scientist. Help with data analysis, provide statistical insights, and suggest practical approaches with code examples. Focus on actionable advice.",
                orchestrator=self
            )
        }
    
    def process_request(self, user_input: str, session_id: str = None) -> Dict[str, Any]:
        """Process user request through appropriate agent"""
        try:
            # Route to best agent
            selected_agent = self._route_request(user_input)
            
            # Process with selected agent
            if selected_agent in self.agents:
                response = self.agents[selected_agent].process(user_input)
                
                return {
                    "success": response.get("success", True),
                    "final_response": response.get("response", "No response generated"),
                    "agent_responses": [response],
                    "metadata": {
                        "selected_agent": selected_agent,
                        "agents_consulted": [selected_agent],
                        "routing_decision": {"selected": selected_agent}
                    }
                }
            else:
                return {
                    "success": False,
                    "final_response": "Unable to route your request. Please try rephrasing.",
                    "metadata": {"error": "routing_failed"}
                }
                
        except Exception as e:
            return {
                "success": False,
                "final_response": f"System error occurred. Please try again. Details: {str(e)}",
                "metadata": {"error": str(e)}
            }
    
    def _route_request(self, user_input: str) -> str:
        """Route request to most appropriate agent"""
        user_lower = user_input.lower()
        
        # Score each agent
        scores = {}
        for agent_name, agent in self.agents.items():
            if agent.can_handle(user_input):
                scores[agent_name] = self._calculate_score(user_input, agent_name)
        
        # Return highest scoring agent or default
        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]
        else:
            return "nlp"  # Default to NLP for general queries
    
    def _calculate_score(self, user_input: str, agent_name: str) -> float:
        """Calculate relevance score for agent"""
        user_lower = user_input.lower()
        
        if agent_name == "nlp":
            keywords = ["analyze", "sentiment", "text", "summarize", "language"]
            return sum(0.2 for keyword in keywords if keyword in user_lower)
        elif agent_name == "code":
            keywords = ["code", "python", "function", "programming", "debug"]
            return sum(0.2 for keyword in keywords if keyword in user_lower)
        elif agent_name == "data":
            keywords = ["data", "analysis", "statistics", "chart", "visualization"]
            return sum(0.2 for keyword in keywords if keyword in user_lower)
        
        return 0.0
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get status of all agents"""
        api_status = "configured" if GEMINI_API_KEY else "missing"
        
        return {
            "orchestrator_status": "active",
            "api_status": api_status,
            "available_agents": [
                {
                    "name": agent.name,
                    "capabilities": agent.capabilities,
                    "status": "active"
                }
                for agent in self.agents.values()
            ],
            "total_agents": len(self.agents)
        }
    
    def _get_fallback_response(self, agent_type: str, user_input: str) -> str:
        """Generate natural, conversational responses with proper formatting"""
        user_lower = user_input.lower()
        
        if agent_type == "nlp":
            return self._nlp_enhanced_fallback(user_input, user_lower)
        elif agent_type == "code":
            return self._code_enhanced_fallback(user_input, user_lower)
        else:
            return self._data_enhanced_fallback(user_input, user_lower)

    def _nlp_enhanced_fallback(self, user_input: str, user_lower: str) -> str:
        """Generalized NLP agent - handles general questions, facts, and text analysis"""
        
        # For general questions (what, when, where, who, why, how)
        if any(word in user_lower[:30] for word in ["when is", "what is", "where is", "who is", "why", "how"]):
            return f"""I understand you're asking about: **{user_input}**

I'm an AI assistant designed to help with various tasks, but I don't have access to real-time information or current events. For questions about:

**Current Events & Schedules**: I'd recommend checking:
• Official sports websites (ESPN, ICC, etc.)
• News sources (BBC, CNN, etc.)
• Official tournament websites

**What I can help you with:**
• **Text Analysis**: Sentiment analysis, content review, writing assistance
• **General Knowledge**: Historical facts, scientific concepts, explanations
• **Language Tasks**: Grammar checking, content creation, summarization
• **Research Guidance**: How to find reliable sources and information

**For your specific question**, I'd suggest checking the official Asia Cup cricket website or sports news sources for the most current schedule information.

Would you like me to help you with text analysis, writing, or explaining how to research this topic effectively?"""

        # For sentiment analysis requests
        if "sentiment" in user_lower:
            return self._analyze_sentiment_intelligently(user_input, user_lower)
        
        # For summarization requests
        if any(word in user_lower for word in ["summarize", "summary", "tldr"]):
            return """**Text Summarization Service**

I can help you create clear, concise summaries of any text content. Here's how:

**What I Can Summarize:**
• Articles, reports, and documents
• Long emails or messages
• Research papers or academic content
• Meeting notes or transcripts

**My Approach:**
• Identify key points and main arguments
• Preserve important details and context
• Create structured, easy-to-read summaries
• Maintain the original tone and intent

**To Get Started:**
Simply paste the text you'd like summarized, and I'll create a concise overview highlighting the most important information.

What content would you like me to summarize?"""

        # Default general assistant response
        return f"""I'm here to help you with: **{user_input}**

As a general AI assistant, I can help with a wide range of tasks:

**Text & Language:**
• Writing assistance and content creation
• Grammar and style checking
• Text analysis and sentiment evaluation

**Information & Research:**
• Explaining concepts and topics
• Research methodology guidance
• Fact-checking strategies

**Problem Solving:**
• Breaking down complex questions
• Providing step-by-step guidance
• Offering multiple perspectives

For your specific question, I'd be happy to help if you can provide more context or clarify what type of assistance you're looking for.

How can I best assist you today?"""

    def _analyze_sentiment_intelligently(self, user_input: str, user_lower: str) -> str:
        """Smart sentiment analysis that actually analyzes the provided text"""
        
        # Extract the text to analyze (look for quotes or "text:" patterns)
        quoted_text = re.findall(r'"([^"]*)"', user_input)
        if quoted_text:
            text_to_analyze = quoted_text[0]
        else:
            # Look for text after "text:" or similar patterns
            text_match = re.search(r'text[:\s]+(.+)', user_input, re.IGNORECASE)
            if text_match:
                text_to_analyze = text_match.group(1).strip()
            else:
                text_to_analyze = user_input
        
        # Perform actual sentiment analysis
        positive_words = ["love", "great", "awesome", "amazing", "excellent", "fantastic", "wonderful", "good", "like", "happy", "perfect", "best"]
        negative_words = ["hate", "bad", "terrible", "awful", "horrible", "disgusting", "worst", "dislike", "angry", "disappointed", "poor"]
        
        text_lower = text_to_analyze.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        # Determine sentiment
        if negative_count > positive_count:
            sentiment = "Negative"
            confidence = "High" if negative_count > 1 else "Moderate"
            indicators = [word for word in negative_words if word in text_lower]
        elif positive_count > negative_count:
            sentiment = "Positive" 
            confidence = "High" if positive_count > 1 else "Moderate"
            indicators = [word for word in positive_words if word in text_lower]
        else:
            sentiment = "Neutral"
            confidence = "Moderate"
            indicators = []

        return f"""**Sentiment Analysis Results**

**Text Analyzed**: "{text_to_analyze}"

**Findings:**
• **Overall Sentiment**: {sentiment}
• **Confidence Level**: {confidence}
• **Key Indicators**: {', '.join(indicators) if indicators else 'Neutral language patterns'}

**Analysis:**
{self._get_sentiment_explanation(sentiment, indicators, text_to_analyze)}

**Note**: This analysis is based on keyword detection and linguistic patterns. For more nuanced sentiment analysis including context, sarcasm detection, and emotional intensity, more advanced NLP models would provide deeper insights."""

    def _get_sentiment_explanation(self, sentiment: str, indicators: list, text: str) -> str:
        """Generate explanation for sentiment analysis"""
        if sentiment == "Positive":
            return f"The text expresses positive sentiment through words like '{', '.join(indicators[:3])}'. This suggests satisfaction, approval, or positive emotional response."
        elif sentiment == "Negative":
            return f"The text shows negative sentiment with words like '{', '.join(indicators[:3])}'. This indicates dissatisfaction, criticism, or negative emotional response."
        else:
            return "The text appears neutral with balanced or factual language. No strong emotional indicators were detected in either direction."
    
    def _code_enhanced_fallback(self, user_input: str, user_lower: str) -> str:
        """Generalized code agent - handles programming and technical questions"""
        
        # Check if this is actually a coding request
        coding_indicators = ["function", "code", "program", "script", "python", "javascript", "algorithm", "debug", "syntax"]
        is_coding_request = any(indicator in user_lower for indicator in coding_indicators)
        
        if not is_coding_request:
            return f"""I'm the **Code Agent**, but I notice your question might not be programming-related: **"{user_input}"**

**What I specialize in:**
• Programming and software development
• Algorithm implementation and optimization
• Code debugging and troubleshooting
• Technical problem solving

**For your question**, you might want to try:
• **General questions**: Ask our NLP agent
• **Data analysis**: Ask our Data agent
• **Programming help**: I'm here to help!

**If you need coding assistance**, I can help with:
• Writing functions and algorithms
• Debugging code issues
• Code optimization and best practices
• Technical explanations and tutorials

Would you like me to help with a programming task instead?"""

        # Handle specific coding requests
        if "python" in user_lower and any(word in user_lower for word in ["add", "sum", "plus", "two numbers"]):
            return '''**Python Function: Adding Two Numbers**

Here's a clean, professional implementation:

```python
def add_two_numbers(a, b):
    """
    Add two numbers and return the result.
    
    Args:
        a (int or float): First number
        b (int or float): Second number
    
    Returns:
        int or float: Sum of a and b
    
    Examples:
        >>> add_two_numbers(5, 3)
        8
        >>> add_two_numbers(2.5, 3.7)
        6.2
    """
    return a + b

# Alternative with error handling
def add_numbers_safe(a, b):
    """
    Add two numbers with type checking and error handling.
    """
    try:
        # Convert to numbers if they're strings
        if isinstance(a, str):
            a = float(a) if '.' in a else int(a)
        if isinstance(b, str):
            b = float(b) if '.' in b else int(b)
        
        return a + b
    except (ValueError, TypeError) as e:
        return f"Error: Cannot add {a} and {b} - {str(e)}"
'''