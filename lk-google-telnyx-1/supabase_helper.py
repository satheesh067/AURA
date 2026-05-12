"""
Supabase helper module for backend services.
Replaces Backboard.io functionality with Supabase queries.
"""
import os
import logging
from typing import Optional, Dict, List
from datetime import datetime

try:
    from supabase import create_client, Client
except ImportError:
    Client = None
    logging.warning("supabase-py not installed. Install with: pip install supabase")

logger = logging.getLogger(__name__)

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.warning("⚠️ SUPABASE_URL or SUPABASE_KEY not set. Supabase queries will fail.")
    supabase_client: Optional[Client] = None
else:
    try:
        supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("✅ Supabase client initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Supabase: {e}")
        supabase_client = None


async def get_user_profile(user_id: str) -> Dict:
    """
    Fetch user profile and recent questionnaire responses.
    Replaces Backboard /recall-memory
    """
    if not supabase_client:
        logger.warning("Supabase not available")
        return {"memory": "", "profile": {}}
    
    try:
        # Fetch profile
        profile_response = supabase_client.table("profiles").select("*").eq("id", user_id).single().execute()
        profile = profile_response.data if profile_response.data else {}
        
        # Fetch latest questionnaire response
        questionnaire_response = (
            supabase_client.table("questionnaire_responses")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        questionnaire = questionnaire_response.data[0] if questionnaire_response.data else {}
        
        # Build memory context from profile and recent responses
        memory_parts = []
        if profile.get("full_name"):
            memory_parts.append(f"User name: {profile['full_name']}")
        if profile.get("age"):
            memory_parts.append(f"Age: {profile['age']}")
        if questionnaire:
            memory_parts.append(f"Recent wellness note: {questionnaire.get('additional_notes', 'N/A')}")
        
        memory = "\n".join(memory_parts)
        
        logger.info(f"✅ Loaded user profile for {user_id}")
        return {
            "memory": memory,
            "profile": profile,
            "questionnaire": questionnaire,
            "name": profile.get("full_name", "")
        }
    except Exception as e:
        logger.error(f"❌ Error fetching user profile: {e}")
        return {"memory": "", "profile": {}, "questionnaire": {}, "name": ""}


async def get_user_reminders(user_id: str) -> List[str]:
    """
    Fetch wellness reminders for the user.
    Replaces Backboard /api/reminders
    """
    if not supabase_client:
        return []
    
    try:
        response = (
            supabase_client.table("reminders")
            .select("reminder_text")
            .eq("user_id", user_id)
            .eq("is_active", True)
            .order("created_at", desc=True)
            .limit(3)
            .execute()
        )
        
        reminders = [r["reminder_text"] for r in response.data] if response.data else []
        logger.info(f"✅ Loaded {len(reminders)} reminders for {user_id}")
        return reminders
    except Exception as e:
        logger.error(f"❌ Error fetching reminders: {e}")
        return []


async def store_session_transcript(
    user_id: str,
    mode: str,
    transcript: List[Dict],
    mood_timeline: List[Dict],
    duration_seconds: int
) -> bool:
    """
    Store session transcript and mood data to Supabase.
    Replaces Backboard /store-transcript
    """
    if not supabase_client:
        return False
    
    try:
        # Create session record
        session_data = {
            "user_id": user_id,
            "mode": mode,
            "duration_seconds": duration_seconds,
            "transcript_summary": "\n".join([f"{m['role']}: {m['content']}" for m in transcript]),
            "mood_summary": mood_timeline[-1]["emotion"] if mood_timeline else "neutral",
            "ended_at": datetime.utcnow().isoformat(),
        }
        
        session_response = supabase_client.table("sessions").insert(session_data).execute()
        session_id = session_response.data[0]["id"] if session_response.data else None
        
        if not session_id:
            return False
        
        # Store individual messages
        for msg in transcript:
            supabase_client.table("messages").insert({
                "session_id": session_id,
                "user_id": user_id,
                "role": msg["role"],
                "content": msg["content"],
            }).execute()
        
        logger.info(f"✅ Stored transcript for session {session_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Error storing transcript: {e}")
        return False


async def get_conversation_history(user_id: str, limit: int = 20) -> List[Dict]:
    """
    Fetch recent conversation history for context.
    Replaces Backboard /recall-memory (conversation context)
    """
    if not supabase_client:
        return []
    
    try:
        # Get recent messages from latest session
        response = (
            supabase_client.table("messages")
            .select("role, content, created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        
        messages = response.data if response.data else []
        messages.reverse()  # Chronological order
        logger.info(f"✅ Loaded {len(messages)} messages for context")
        return messages
    except Exception as e:
        logger.error(f"❌ Error fetching conversation history: {e}")
        return []


async def search_knowledge_base(query: str) -> Optional[str]:
    """
    Search knowledge base for Q&A pairs.
    Replaces Backboard /query-knowledge
    """
    if not supabase_client:
        return None
    
    try:
        # Simple text search in knowledge_base table
        response = (
            supabase_client.table("knowledge_base")
            .select("answer")
            .ilike("question", f"%{query}%")  # Case-insensitive search
            .limit(1)
            .execute()
        )
        
        answer = response.data[0]["answer"] if response.data else None
        if answer:
            logger.info(f"✅ Found knowledge base answer for: {query}")
        return answer
    except Exception as e:
        logger.error(f"❌ Error searching knowledge base: {e}")
        return None


async def store_user_context(user_id: str, context: str) -> bool:
    """
    Store/update user context from questionnaire or session.
    Replaces Backboard /api/memory/store
    """
    if not supabase_client:
        return False
    
    try:
        # Update profile with context note
        supabase_client.table("profiles").update({
            "context_note": context,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", user_id).execute()
        
        logger.info(f"✅ Stored context for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Error storing user context: {e}")
        return False
