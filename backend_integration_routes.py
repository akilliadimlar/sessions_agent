from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from bson import ObjectId
import os
import openai
from datetime import datetime

# Assuming you have a database connection similar to this
# from .db import db  # Your existing database connection

# Initialize OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Create router for analysis endpoints
analysis_router = APIRouter(prefix="/analysis", tags=["Analysis"])

# Pydantic models for request/response
class StepResult(BaseModel):
    step_id: int
    step_type: str  # AI_CONVERSATION, AI_CV_GAME, AI_QUIZ
    is_successful: Optional[bool] = None
    duration_seconds: Optional[int] = None
    details: Optional[Dict[str, Any]] = None

class StepAnalysisRequest(BaseModel):
    session_id: str
    step_result: StepResult

class SessionInitRequest(BaseModel):
    session_id: str

# Analysis Routes
@analysis_router.post("/session/initialize")
async def initialize_session_analysis(request: SessionInitRequest):
    """Initialize analysis when session starts"""
    try:
        # Convert string to ObjectId
        session_oid = ObjectId(request.session_id)
        
        # Get session, child, and lesson data
        session = await db.sessions.find_one({"_id": session_oid})
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
            
        child = await db.children.find_one({"_id": session["child_id"]})
        lesson = await db.lessons.find_one({"_id": session["lesson_id"]})
        
        # Create initial LLM report document
        llm_report = {
            "_id": ObjectId(),
            "session_id": request.session_id,
            "child_id": str(session["child_id"]),
            "step_reports": {
                "voice_reports": {},
                "game_reports": {},
                "test_reports": {},
                "final_report": {},
                "suggestion": {}
            },
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Insert initial report
        result = await db.llm_reports.insert_one(llm_report)
        
        return {
            "status": "success",
            "message": "Session analysis initialized",
            "report_id": str(result.inserted_id),
            "session_info": {
                "child_name": child.get("name") if child else "Unknown",
                "lesson_name": lesson.get("lesson_name") if lesson else "Unknown"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize session: {str(e)}")

@analysis_router.post("/session/analyze-step")
async def analyze_step_completion(request: StepAnalysisRequest):
    """Analyze step completion and update report"""
    try:
        session_oid = ObjectId(request.session_id)
        
        # Get session data
        session = await db.sessions.find_one({"_id": session_oid})
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
            
        # Get child and lesson data for context
        child = await db.children.find_one({"_id": session["child_id"]})
        lesson = await db.lessons.find_one({"_id": session["lesson_id"]})
        
        # Get current LLM report
        llm_report = await db.llm_reports.find_one({"session_id": request.session_id})
        if not llm_report:
            raise HTTPException(status_code=404, detail="LLM report not found")
        
        # Generate step analysis
        step_analysis = await generate_step_analysis(
            request.step_result, session, child, lesson
        )
        
        # Update the appropriate report section
        step_type = request.step_result.step_type
        step_reports = llm_report["step_reports"]
        
        if step_type == "AI_CONVERSATION":
            step_reports["voice_reports"][f"step_{request.step_result.step_id}"] = step_analysis
        elif step_type == "AI_CV_GAME":
            step_reports["game_reports"][f"step_{request.step_result.step_id}"] = step_analysis
        elif step_type == "AI_QUIZ":
            step_reports["test_reports"][f"step_{request.step_result.step_id}"] = step_analysis
        
        # Update the document
        await db.llm_reports.update_one(
            {"_id": llm_report["_id"]},
            {
                "$set": {
                    "step_reports": step_reports,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return {
            "status": "success",
            "message": f"Step {request.step_result.step_id} analysis completed",
            "analysis": step_analysis
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze step: {str(e)}")

@analysis_router.get("/session/{session_id}/report")
async def get_session_report(session_id: str):
    """Get current session analysis report"""
    try:
        llm_report = await db.llm_reports.find_one({"session_id": session_id})
        if not llm_report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        # Convert ObjectId to string for JSON serialization
        llm_report["_id"] = str(llm_report["_id"])
        
        return {
            "status": "success",
            "report": llm_report
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get report: {str(e)}")

@analysis_router.post("/session/{session_id}/finalize")
async def finalize_session_analysis(session_id: str):
    """Finalize session when it ends"""
    try:
        session_oid = ObjectId(session_id)
        
        # Get complete session data
        session = await db.sessions.find_one({"_id": session_oid})
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
            
        child = await db.children.find_one({"_id": session["child_id"]})
        lesson = await db.lessons.find_one({"_id": session["lesson_id"]})
        
        # Get LLM report
        llm_report = await db.llm_reports.find_one({"session_id": session_id})
        if not llm_report:
            raise HTTPException(status_code=404, detail="LLM report not found")
        
        # Generate final analysis
        final_analysis = await generate_final_analysis(session, child, lesson, llm_report)
        
        # Update with final report
        await db.llm_reports.update_one(
            {"_id": llm_report["_id"]},
            {
                "$set": {
                    "step_reports.final_report": final_analysis["final_report"],
                    "step_reports.suggestion": final_analysis["suggestions"],
                    "finalized_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return {
            "status": "success",
            "message": "Session analysis finalized",
            "final_analysis": final_analysis
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to finalize session: {str(e)}")

# Helper functions for analysis
async def generate_step_analysis(step_result: StepResult, session: dict, child: dict, lesson: dict) -> dict:
    """Generate LLM analysis for a specific step"""
    try:
        # Prepare context for analysis
        context = {
            "child_name": child.get("name", "Unknown") if child else "Unknown",
            "child_age": calculate_age(child.get("birthdate")) if child and child.get("birthdate") else "Unknown",
            "lesson_name": lesson.get("lesson_name", "Unknown") if lesson else "Unknown",
            "step_type": step_result.step_type,
            "step_id": step_result.step_id,
            "is_successful": step_result.is_successful,
            "duration_seconds": step_result.duration_seconds,
            "details": step_result.details
        }
        
        # Create specific prompt based on step type
        if step_result.step_type == "AI_CONVERSATION":
            prompt = f"""
            Çocuğun ses etkileşimi performansını analiz et:
            
            Çocuk: {context['child_name']} (Yaş: {context['child_age']})
            Ders: {context['lesson_name']}
            Adım: {context['step_id']} - {context['step_type']}
            Başarılı: {context['is_successful']}
            Süre: {context['duration_seconds']} saniye
            Detaylar: {context['details']}
            
            Lütfen şunları değerlendir:
            1. Çocuğun katılım düzeyi
            2. İletişim becerileri  
            3. Öğrenme göstergeleri
            4. Öneriler
            """
        elif step_result.step_type == "AI_CV_GAME":
            prompt = f"""
            Çocuğun görsel oyun performansını analiz et:
            
            Çocuk: {context['child_name']} (Yaş: {context['child_age']})
            Ders: {context['lesson_name']}
            Adım: {context['step_id']} - {context['step_type']}
            Başarılı: {context['is_successful']}
            Süre: {context['duration_seconds']} saniye
            Detaylar: {context['details']}
            
            Lütfen şunları değerlendir:
            1. Görsel algı becerileri
            2. El-göz koordinasyonu
            3. Problem çözme yaklaşımı
            4. Öneriler
            """
        elif step_result.step_type == "AI_QUIZ":
            prompt = f"""
            Çocuğun quiz performansını analiz et:
            
            Çocuk: {context['child_name']} (Yaş: {context['child_age']})
            Ders: {context['lesson_name']}
            Adım: {context['step_id']} - {context['step_type']}
            Başarılı: {context['is_successful']}
            Süre: {context['duration_seconds']} saniye
            Detaylar: {context['details']}
            
            Lütfen şunları değerlendir:
            1. Anlama düzeyi
            2. Doğru cevap oranı
            3. Kavram öğrenme durumu
            4. Öneriler
            """
        
        # Call OpenAI API
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Sen eğitim uzmanısın. Çocukların öğrenme performansını analiz ediyorsun."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=400,
            temperature=0.7
        )
        
        analysis_text = response['choices'][0]['message']['content']
        
        return {
            "step_id": step_result.step_id,
            "step_type": step_result.step_type,
            "analysis": analysis_text,
            "performance_score": calculate_performance_score(step_result),
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "step_id": step_result.step_id,
            "step_type": step_result.step_type,
            "analysis": f"Analiz hatası: {str(e)}",
            "performance_score": 0,
            "generated_at": datetime.utcnow().isoformat()
        }

async def generate_final_analysis(session: dict, child: dict, lesson: dict, llm_report: dict) -> dict:
    """Generate final comprehensive analysis"""
    try:
        # Compile all step analyses
        all_reports = llm_report["step_reports"]
        
        context = {
            "child_name": child.get("name", "Unknown") if child else "Unknown",
            "lesson_name": lesson.get("lesson_name", "Unknown") if lesson else "Unknown",
            "total_score": session.get("total_score"),
            "status": session.get("status"),
            "step_reports": all_reports
        }
        
        prompt = f"""
        Çocuğun genel öğrenme performansını analiz et:
        
        Çocuk: {context['child_name']}
        Ders: {context['lesson_name']}
        Genel Skor: {context['total_score']}
        Durum: {context['status']}
        
        Adım Raporları: {context['step_reports']}
        
        Lütfen kapsamlı bir değerlendirme yap:
        1. Genel performans özeti
        2. Güçlü yönler
        3. Gelişim alanları
        4. Gelecek dersler için öneriler
        5. Ebeveyn tavsiyeleri
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Sen çocuk eğitimi uzmanısın. Kapsamlı öğrenme değerlendirmeleri yapıyorsun."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=600,
            temperature=0.7
        )
        
        final_text = response['choices'][0]['message']['content']
        
        return {
            "final_report": final_text,
            "suggestions": extract_suggestions(final_text),
            "overall_score": calculate_overall_score(session, all_reports),
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "final_report": f"Final analiz hatası: {str(e)}",
            "suggestions": ["Teknik hata nedeniyle öneri üretilemedi"],
            "overall_score": 0,
            "generated_at": datetime.utcnow().isoformat()
        }

# Utility functions
def calculate_age(birthdate) -> int:
    """Calculate age from birthdate"""
    try:
        today = datetime.now()
        age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
        return age
    except:
        return 0

def calculate_performance_score(step_result: StepResult) -> int:
    """Calculate performance score for a step"""
    if step_result.is_successful is None:
        return 0
    
    base_score = 100 if step_result.is_successful else 30
    
    # Adjust based on duration (if available)
    if step_result.duration_seconds:
        if step_result.duration_seconds < 60:  # Very fast
            base_score *= 0.8
        elif step_result.duration_seconds > 300:  # Very slow
            base_score *= 0.9
    
    return min(100, max(0, int(base_score)))

def calculate_overall_score(session: dict, all_reports: dict) -> int:
    """Calculate overall session score"""
    try:
        return session.get("total_score", 0)
    except:
        return 0

def extract_suggestions(final_text: str) -> List[str]:
    """Extract actionable suggestions from final analysis"""
    # Simple extraction - can be improved with more sophisticated NLP
    suggestions = []
    lines = final_text.split('\n')
    
    for line in lines:
        line = line.strip()
        if any(keyword in line.lower() for keyword in ['öneri', 'tavsiye', 'gelişim', 'çalış']):
            if len(line) > 10:  # Meaningful suggestions
                suggestions.append(line)
    
    return suggestions[:5]  # Limit to 5 suggestions