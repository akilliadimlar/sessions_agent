import os
import openai
from dotenv import load_dotenv

load_dotenv()

# Configure OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

def analyze_session(session: dict) -> dict:
    steps = session.get('step_results', [])
    completed_steps = [s for s in steps if s.get('is_successful')]
    avg_duration = sum(s.get('duration_seconds', 0) for s in steps) / len(steps) if steps else 0

    # Generate LLM analysis
    llm_summary = generate_llm_analysis(session)
    
    return {
        "session_id": session.get('_id'),
        "summary": llm_summary,
        "metrics": {
            "total_steps": len(steps),
            "completed_steps": len(completed_steps),
            "average_step_duration": avg_duration
        }
    }

def generate_llm_analysis(session: dict) -> str:
    """Generate real-time LLM analysis of the session"""
    try:
        # Prepare session data for analysis
        session_info = {
            "session_id": session.get('_id'),
            "lesson_id": session.get('lesson_id'),
            "child_id": session.get('child_id'),
            "status": session.get('status'),
            "total_score": session.get('total_score'),
            "step_results": session.get('step_results', [])
        }
        
        # Create prompt for LLM
        prompt = f"""
        Analyze this educational session data and provide insights in Turkish:
        
        Session Data: {session_info}
        
        Please provide:
        1. Overall performance assessment
        2. Areas of strength and weakness
        3. Recommendations for improvement
        4. Learning progress insights
        
        Keep the response concise and educational-focused.
        """
        
        # Call OpenAI API
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an educational assessment expert. Analyze session data and provide insights in Turkish."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.7
        )
        
        return response['choices'][0]['message']['content']
        
    except Exception as e:
        # Fallback to original summary if LLM fails
        return session.get('llm_analysis_report', 'LLM analysis failed. Using original summary.')