"""
Simplified Gemini AI service for real estate conversations.
Ultra-short, direct responses with minimal fluff.
Fast responses using gemini-2.5-flash-lite model.
"""

import logging
from flask import current_app
from google import genai
from google.genai import types
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class GeminiServiceSimple:
    """Simplified service for generating ultra-short, direct responses"""
    
    def __init__(self):
        """Initialize Gemini service with fast model"""
        self.client = None
        self.model_name = None
        self._initialized = False
    
    def _initialize_model(self):
        """Initialize the Gemini model with fast settings"""
        try:
            # Initialize the new Gemini client
            self.client = genai.Client(api_key=current_app.config['GEMINI_API_KEY'])
            
            # Use flash-lite model for speed
            self.model_name = current_app.config.get('GEMINI_MODEL', 'gemini-2.5-flash-lite')
            
            self._initialized = True
            logger.info(f"Gemini AI model '{self.model_name}' initialized successfully (simple mode)")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini model: {str(e)}")
            raise
    
    def _ensure_initialized(self):
        """Ensure the model is initialized"""
        if not self._initialized:
            self._initialize_model()
    
    def generate_response(self, stage: str, lead_data: Dict[str, Any], conversation_history: List[Dict], user_message: str) -> str:
        """
        Generate ultra-short, direct AI response
        
        Args:
            stage: Current lead stage
            lead_data: Lead information
            conversation_history: Recent conversation history
            user_message: Current user message
            
        Returns:
            str: Ultra-short response in Hebrew (2-3 sentences max)
        """
        self._ensure_initialized()
        
        try:
            logger.info(f"Generating simple response for lead {lead_data.get('id')} in stage: {stage}")
            
            # Build ultra-short prompt
            prompt = self._build_simple_prompt(stage, lead_data, conversation_history, user_message)
            
            # Try simple API call first (like working version)
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
            except Exception as e:
                logger.warning(f"Simple API call failed, trying with config: {e}")
                # Fallback with config
                generation_config = types.GenerateContentConfig(
                    temperature=0.8,
                    max_output_tokens=600  # Increased even more
                )
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=generation_config
                )
            
            # Extract response text using proper Gemini API structure
            response_text = ""
            try:
                # Method 1: Direct text attribute (newer API)
                if hasattr(response, 'text') and response.text:
                    response_text = response.text.strip()
                else:
                    # Method 2: Candidates structure (older API)
                    if hasattr(response, 'candidates') and response.candidates:
                        for i, candidate in enumerate(response.candidates):
                            # Check if candidate has finish_reason MAX_TOKENS
                            if hasattr(candidate, 'finish_reason') and candidate.finish_reason:
                                if 'MAX_TOKENS' in str(candidate.finish_reason):
                                    logger.warning("Response was cut off due to token limit")
                                    response_text = "מה השם שלך?"  # Simple fallback
                                    break
                            
                            if hasattr(candidate, 'content') and candidate.content:
                                content = candidate.content
                                if hasattr(content, 'parts') and content.parts:
                                    for j, part in enumerate(content.parts):
                                        if hasattr(part, 'text') and part.text:
                                            response_text += part.text
                        response_text = response_text.strip()
                
                # If still empty, provide fallback
                if not response_text:
                    logger.warning(f"Empty response from {self.model_name}, using fallback")
                    response_text = "מה השם שלך?"
                    
            except Exception as e:
                logger.error(f"Error extracting response from {self.model_name}: {e}")
                response_text = "מה השם שלך?"
            
            # Clean response - remove any prompt artifacts
            response_text = self._clean_response(response_text)
            
            # Format for WhatsApp
            response_text = self._format_for_whatsapp(response_text)
            
            logger.info(f"Simple response generated for lead {lead_data.get('id')}, length: {len(response_text)}")
            return response_text
            
        except Exception as e:
            logger.error(f"Error generating simple response: {str(e)}")
            return "מצטער, יש לי בעיה טכנית. נסה שוב."
    
    def _build_simple_prompt(self, stage: str, lead_data: Dict, conversation_history: List[Dict], user_message: str) -> str:
        """Build prompt with proper context like working version"""
        
        # Base prompt
        prompt = "אתה סוכן נדל\"ן. ענה בעברית קצר (1-2 משפטים).\n\n"
        
        # Add conversation history (like working version)
        if conversation_history:
            recent_messages = conversation_history[-5:]  # Last 5 messages for context
            if recent_messages:
                prompt += "השיחה עד עכשיו:\n"
                for msg in recent_messages:
                    sender = "בוט" if msg['message_type'] == 'bot' else "לקוח"
                    prompt += f"{sender}: {msg['content']}\n"
                prompt += "\n"
        
        # What we know about the lead (like working version)
        context_parts = []
        if lead_data.get('name'):
            context_parts.append(f"שם: {lead_data['name']}")
        if lead_data.get('preferred_area'):
            context_parts.append(f"פרויקט: {lead_data['preferred_area']}")
        if lead_data.get('rooms'):
            context_parts.append(f"חדרים: {lead_data['rooms']}")
        if lead_data.get('budget'):
            context_parts.append(f"תקציב: {lead_data['budget']}")
        
        if context_parts:
            prompt += "מה שאתה יודע:\n" + "\n".join(context_parts) + "\n\n"
        
        # Current message
        prompt += f"הלקוח אמר: {user_message}\n\n"
        
        # Task based on stage - DON'T use client name in response
        if stage == 'new':
            prompt += "שאל: מה השם שלך? (אל תשתמש בשם בתשובה)"
        elif stage == 'collecting_profile':
            if not lead_data.get('name'):
                prompt += "שאל: מה השם שלך?"
            elif not lead_data.get('preferred_area'):
                # Include available properties in the prompt
                if lead_data.get('available_properties'):
                    properties_list = ', '.join(lead_data['available_properties'])
                    prompt += f"שאל: באיזה פרויקט מתעניין? (אל תשתמש בשם)\n\n"
                    prompt += f"חשוב: הזכר רק את השמות האלה בדיוק כמו שהם: {properties_list}\nאל תמציא שמות אחרים!"
                else:
                    prompt += "שאל: באיזה פרויקט מתעניין? (אל תשתמש בשם)"
            elif not lead_data.get('rooms'):
                prompt += "שאל: כמה חדרים? (אל תשתמש בשם)"
            else:
                prompt += "אמור: אחפש דירות (אל תשתמש בשם)"
        elif stage == 'qualified':
            prompt += "שאל: רוצה לתאם ביקור? (אל תשתמש בשם)"
        else:
            prompt += "עזור בקצרה"
        
        return prompt
    
    def _build_context(self, lead_data: Dict) -> str:
        """Build ultra-short context about lead"""
        parts = []
        
        if lead_data.get('name'):
            parts.append(f"שם: {lead_data['name']}")
        if lead_data.get('preferred_area'):
            parts.append(f"פרויקט: {lead_data['preferred_area']}")
        if lead_data.get('rooms'):
            parts.append(f"חדרים: {lead_data['rooms']}")
        if lead_data.get('budget'):
            parts.append(f"תקציב: {lead_data['budget']:,.0f}₪")
        if lead_data.get('has_parking') is not None:
            parts.append(f"חניה: {'כן' if lead_data['has_parking'] else 'לא'}")
        
        return "\n".join([f"- {p}" for p in parts]) if parts else ""
    
    def _get_stage_guidance(self, stage: str, lead_data: Dict) -> str:
        """Get ultra-short stage guidance"""
        
        guidance = {
            'new': """
🎯 לקוח חדש - קבל אותו בקצרה ושאל את השם שלו.""",
            
            'collecting_profile': f"""
🎯 צריך לאסוף:
{self._get_missing_fields(lead_data)}
שאל רק על שדה אחד בכל פעם.""",
            
            'qualified': """
🎯 יש את כל המידע - הצע לו לראות דירות זמינות.""",
            
            'showing_properties': """
🎯 תציג דירות - אחרי זה תשאל אם רוצה לתאם ביקור.""",
            
            'scheduling_in_progress': """
🎯 שלחת קישור לקלנדלי - חכה לאישור שקבע.""",
            
            'tour_scheduled': """
🎯 הפגישה קבועה - ענה רק על שאלות על הפגישה.""",
            
            'asking_guarantees': """
🎯 הסבר על דרישות הערבויות בקצרה:
- תלושי שכר מ-2 חודשים אחרונים
- ערבות של 2 חודשי שכירות מראש
אם מסכים - תשלח קלנדלי."""
        }
        
        return guidance.get(stage, f"🎯 שלב {stage} - ענה בקצרה ולעניין")
    
    def _get_missing_fields(self, lead_data: Dict) -> str:
        """Get list of missing fields"""
        missing = []
        if not lead_data.get('preferred_area'):
            missing.append("- איזה פרויקט? (Sderot Yerushalayim / Neve Sharet / Afar House)")
        if not lead_data.get('rooms'):
            missing.append("- כמה חדרים?")
        
        return "\n".join(missing) if missing else "- הכל יש!"
    
    def _format_for_whatsapp(self, response: str) -> str:
        """Format response for WhatsApp - minimal changes"""
        # Convert ** to * for WhatsApp bold
        response = response.replace("**", "*")
        
        # Remove AI artifacts
        response = response.replace("בוט", "").replace("AI", "")
        
        # Ensure not too long
        if len(response) > 500:
            response = response[:497] + "..."
        
        return response.strip()
    
    def _clean_response(self, response: str) -> str:
        """Clean response to remove prompt artifacts"""
        if not response:
            return response
            
        # Remove common prompt artifacts
        lines = response.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            # Skip lines that look like prompt data
            if (line.startswith('שם:') and 'הלקוח:' in line) or \
               line.startswith('מה שאתה יודע:') or \
               line.startswith('השיחה עד עכשיו:') or \
               line.startswith('הלקוח אמר:') or \
               line.startswith('שאל:') or \
               line.startswith('אמור:'):
                continue
            # Keep actual response lines
            if line and not line.startswith('שם:') and not line.startswith('הלקוח:'):
                cleaned_lines.append(line)
        
        # If we have cleaned lines, use them
        if cleaned_lines:
            return '\n'.join(cleaned_lines).strip()
        
        # Fallback to original response
        return response.strip()
    
    def generate_property_message(self, lead_data: Dict, properties: List[Dict]) -> str:
        """Generate ultra-short property recommendation"""
        self._ensure_initialized()
        
        try:
            # Ultra simple prompt
            prop = properties[0]
            prop_info = prop.get('properties', {}) if isinstance(prop.get('properties'), dict) else {}
            prompt = f"""סוכן נדל"ן. ענה בעברית קצר.

מצאתי: {prop.get('rooms')} חדרים ב-{lead_data.get('preferred_area', '')} - {prop.get('price'):,.0f}₪/חודש

אמור: יש דירות. שולח תמונות. רוצה פרטים או לתאם ביקור?"""
            
            generation_config = types.GenerateContentConfig(
                temperature=0.8,
                max_output_tokens=300  # Increased - was cutting off responses
            )
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=generation_config
            )
            
            # Extract text with proper error handling (same as old working version)
            response_text = ""
            try:
                if hasattr(response, 'text') and response.text:
                    response_text = response.text.strip()
                elif hasattr(response, 'candidates') and response.candidates:
                    for candidate in response.candidates:
                        if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                            for part in candidate.content.parts:
                                if hasattr(part, 'text') and part.text:
                                    response_text += part.text
                
                response_text = response_text.strip()
                
                if not response_text:
                    logger.warning(f"Empty property message from {self.model_name}")
                    response_text = f"מצאתי {len(properties)} דירות מתאימות. שולח תמונות..."
                    
            except Exception as e:
                logger.error(f"Error extracting property message from {self.model_name}: {e}")
                response_text = f"מצאתי {len(properties)} דירות מתאימות. שולח תמונות..."
            
            return self._format_for_whatsapp(response_text)
            
        except Exception as e:
            logger.error(f"Error generating property message: {e}")
            return f"מצאתי {len(properties)} דירות מתאימות. שולח תמונות..."
    
    def generate_no_properties_message(self, lead_data: Dict) -> str:
        """Generate ultra-short message when no properties found"""
        self._ensure_initialized()
        
        try:
            # Ultra simple prompt
            prompt = f"""סוכן נדל"ן. ענה בעברית קצר.

חיפש: {lead_data.get('rooms')} חדרים ב-{lead_data.get('preferred_area', '')}

אמור: לא מצאתי. גמיש בפרויקט או חדרים?"""
            
            generation_config = types.GenerateContentConfig(
                temperature=0.8,
                max_output_tokens=250  # Increased - was cutting off responses
            )
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=generation_config
            )
            
            # Extract text with proper error handling (same as old working version)
            response_text = ""
            try:
                if hasattr(response, 'text') and response.text:
                    response_text = response.text.strip()
                elif hasattr(response, 'candidates') and response.candidates:
                    for candidate in response.candidates:
                        if hasattr(candidate, 'content') and candidate.content:
                            content = candidate.content
                            if hasattr(content, 'parts') and content.parts:
                                for part in content.parts:
                                    if hasattr(part, 'text') and part.text:
                                        response_text += part.text
                
                response_text = response_text.strip()
                
                if not response_text:
                    logger.warning(f"Empty no properties message from {self.model_name}, using AI to generate")
                    # Generate a simple fallback using AI
                    response_text = self.generate_response('collecting_profile', lead_data, [], f"לא מצאתי דירות עם {lead_data.get('rooms')} חדרים ב-{lead_data.get('preferred_area')}. גמיש?")
                    
            except Exception as e:
                logger.error(f"Error extracting no properties message from {self.model_name}: {e}")
                # Generate a simple fallback using AI
                response_text = self.generate_response('collecting_profile', lead_data, [], f"לא מצאתי דירות עם {lead_data.get('rooms')} חדרים ב-{lead_data.get('preferred_area')}. גמיש?")
            
            response_text = self._clean_response(response_text)
            
            return self._format_for_whatsapp(response_text)
            
        except Exception as e:
            logger.error(f"Error generating no properties message: {e}")
            return "לא מצאתי בדיוק מה שחיפשת. גמיש בפרויקט או במספר חדרים?"


# Global instance
gemini_service_simple = GeminiServiceSimple()

