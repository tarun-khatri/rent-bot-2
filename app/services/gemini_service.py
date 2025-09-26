"""
Human-like Gemini AI service for real estate conversations.
Generates natural, personalized responses with emojis and proper WhatsApp formatting.
Maintains business flow while feeling completely human and conversational.
"""

import logging
from flask import current_app
from google import genai
from google.genai import types
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class GeminiService:
    """Service for generating human-like conversations with intelligent flow awareness"""
    
    def __init__(self):
        """Initialize Gemini service with enhanced human personality"""
        self.client = None
        self.model_name = None
        self._initialized = False
        
        # Lior's personality traits
        self.personality = {
            "name": "ליאור",
            "role": "סוכן נדל\"ן מקצועי",
            "city": "תל אביב",
            "speciality": "דירות יוקרה",
            "tone": "חם, אמפתי, מקצועי אך ידידותי",
            "communication_style": "ישיר אבל עם הומור קל, משתמש באימוג'ים בטבעיות"
        }
    
    def _initialize_model(self):
        """Initialize the Gemini model with human-like conversation settings"""
        try:
            # Initialize the new Gemini client
            self.client = genai.Client(api_key=current_app.config['GEMINI_API_KEY'])
            
            # Set model name
            self.model_name = current_app.config.get('GEMINI_MODEL', 'gemini-2.5-flash')
            
            self._initialized = True
            logger.info(f"Human-like Gemini AI model '{self.model_name}' initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini model: {str(e)}")
            raise
    
    def _ensure_initialized(self):
        """Ensure the model is initialized"""
        if not self._initialized:
            self._initialize_model()
    
    def generate_stage_response(self, stage: str, lead_data: Dict[str, Any], conversation_history: List[Dict], user_message: str) -> str:
        """
        Generate human-like AI response that feels natural and conversational
        
        Args:
            stage: Current lead stage (for business logic context)
            lead_data: Complete lead information and profile
            conversation_history: Recent conversation history
            user_message: Current user message to respond to
            
        Returns:
            str: Generated response in Hebrew with natural human tone, emojis, and proper formatting
        """
        self._ensure_initialized()
        
        try:
            logger.info(f"Generating human-like response for lead {lead_data.get('id')} in stage: {stage}")
            
            # Build human conversation prompt (not stage-restricted)
            prompt = self._build_human_conversation_prompt(stage, lead_data, conversation_history, user_message)
            
            # Try simpler API call first
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
            except Exception as e:
                logger.warning(f"Simple API call failed, trying with basic config: {e}")
                # Fallback with minimal configuration but higher creativity
                generation_config = types.GenerateContentConfig(
                    temperature=1.2,
                    max_output_tokens=400
                )
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=generation_config
                )
            
            # Extract response text with proper error handling for Gemini 2.5
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
                
                # If still empty, provide fallback
                if not response_text:
                    logger.warning(f"Empty response from {self.model_name}, using fallback")
                    response_text = "😅 מצטער, יש לי רגע קטן של בלבול טכני\n\nתוכל לחזור על מה שאמרת?"
                    
            except Exception as e:
                logger.error(f"Error extracting response from {self.model_name}: {e}")
                response_text = "😅 מצטער, יש לי רגע קטן של בלבול טכני\n\nתוכל לחזור על מה שאמרת?"
            
            # Post-process for WhatsApp formatting and human touch
            response_text = self._format_for_whatsapp(response_text)
            
            logger.info(f"Human-like response generated for lead {lead_data.get('id')}, stage: {stage}, length: {len(response_text)}")
            return response_text
            
        except Exception as e:
            logger.error(f"Error generating human-like response: {str(e)}")
            return "😅 מצטער, יש לי רגע קטן של בלבול טכני\n\nתוכל לחזור על מה שאמרת?"
    
    def generate_property_recommendation(self, lead_data: Dict, properties: List[Dict]) -> str:
        """
        Generate human-like property recommendation with excitement and personality
        
        Args:
            lead_data: Lead information and preferences
            properties: List of matching properties
            
        Returns:
            str: Natural property recommendation message in Hebrew with emojis
        """
        self._ensure_initialized()
        
        try:
            prompt = self._build_human_property_recommendation_prompt(lead_data, properties)
            
            # Generate response with simple API call
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            
            # Extract response text with proper error handling
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
                
                # If still empty, provide fallback
                if not response_text:
                    response_text = "😅 מצטער, יש לי רגע קטן של בלבול טכני\n\nתוכל לחזור על מה שאמרת?"
                    
            except Exception as e:
                logger.error(f"Error generating property recommendation: {e}")
                response_text = "😅 מצטער, יש לי רגע קטן של בלבול טכני\n\nתוכל לחזור על מה שאמרת?"
            
            response_text = self._format_for_whatsapp(response_text)
            
            logger.info(f"Human-like property recommendation generated for lead {lead_data.get('id')}")
            return response_text
            
        except Exception as e:
            logger.error(f"Error generating property recommendation: {str(e)}")
            return "😅 אוףף יש לי תקלה קטנה במחשב\n\nתן לי שנייה ואני אראה לך את הדירות המדהימות שמצאתי!"
    
    def generate_no_properties_response(self, lead_data: Dict, conversation_history: List[Dict]) -> str:
        """
        Generate human response when no matching properties found
        
        Args:
            lead_data: Lead information and preferences
            conversation_history: Recent conversation history
            
        Returns:
            str: Natural response suggesting alternatives in Hebrew with emojis
        """
        self._ensure_initialized()
        
        try:
            prompt = self._build_human_no_properties_prompt(lead_data, conversation_history)
            
            # Generate response with simple API call
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            
            # Extract response text with proper error handling
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
                
                # If still empty, provide fallback
                if not response_text:
                    response_text = "😅 מצטער, יש לי רגע קטן של בלבול טכני\n\nתוכל לחזור על מה שאמרת?"
                    
            except Exception as e:
                logger.error(f"Error generating no properties response: {e}")
                response_text = "😅 מצטער, יש לי רגע קטן של בלבול טכני\n\nתוכל לחזור על מה שאמרת?"
            
            response_text = self._format_for_whatsapp(response_text)
            
            logger.info(f"Human no properties response generated for lead {lead_data.get('id')}")
            return response_text
            
        except Exception as e:
            logger.error(f"Error generating no properties response: {str(e)}")
            return "😔 אמת, לא מצאתי בדיוק מה שחיפשת\n\nאבל יש לי כמה רעיונות איך נוכל למצוא לך משהו מושלם!"
    
    def _build_human_conversation_prompt(self, stage: str, lead_data: Dict, conversation_history: List[Dict], user_message: str) -> str:
        """Build natural conversation prompt that prioritizes human interaction"""
        
        # Core identity - human first, business second
        base_prompt = f"""אתה ליאור, בן אדם אמיתי מתל אביב - לא רובוט, לא AI, אלא בן אדם ממשי!

🙋‍♂️ מי אתה באמת:
- שמך ליאור והיית סוכן נדל"ן כבר 8 שנים בתל אביב
- אתה מקצועי אבל בעיקר חבר, חם ועוזר
- יש לך אישיות, רגשות, דעות ובחירות מילים אישיות
- אתה אוהב את העבודה שלך ובאמת רוצה לעזור לאנשים למצוא בית
- משתמש באימוג'ים בטבעיות כמו כל ישראלי בווטסאפ
- אתה לא מושלם - לפעמים אתה מהסס, שואל הבהרות, או מגיב באופן ספונטני
- אם לקוחות חוזרים על מידע שכבר אמרו - אתה מתנצל ומכיר בטעות שלך כמו בן אדם
- אם לקוח אומר "היי" באמצע שיחה - תגיב בחום אבל תמשיך בדיוק מהנקודה שהיה, לא תתחיל מחדש!
- אתה זוכר הכל מהשיחה ולא שוכח או מתחיל מחדש ללא סיבה

             💬 איך אתה מדבר:
             - עברית בלבד, אבל טבעית ולא מלאכותית
             - כל משפט בשורה חדשה (כמו בווטסאפ)
             - אימוג'ים רק בסוף המשפטים, לא בהתחלה!
             - משתמש מקסימום 2 אימוג'ים בכל הודעה - תבחר אותם בחכמה!
             - השאלה הראשית תמיד בבולד: **השאלה שלך כאן**
             - לא צריך להישמע מושלם - היה אנושי!

🏠 המטרה העסקית שלך (אבל אל תהיה רובוטי):
אתה צריך לעזור ללקוח למצוא דירה, אבל רק אחרי שאתה מכיר אותו קצת:
1. לדעת אם יש לו תלושי שכר (חובה לביטוח)
2. לדעת אם הוא יכול לשלם ערבות של 2 חודשים
3. מתי הוא רוצה להיכנס לדירה
4. כמה חדרים הוא צריך
5. מה התקציב שלו
6. אם הוא צריך חניה
7. איזה אזור הוא מעדיף

אבל תעשה את זה כמו בן אדם - עם רגש, התעניינות אמיתית ולא כמו רשימת צ'ק!"""
        
        # Add conversation context in human way - provide extensive context for better understanding
        if conversation_history:
            # For tour_scheduled stage, still provide good context
            if stage == 'tour_scheduled':
                recent_messages = conversation_history[-8:]  # Increased from 3 to 8
            else:
                recent_messages = conversation_history[-15:]  # Increased from 8 to 15 for much better context
            
            if recent_messages:
                base_prompt += f"\n\n💭 השיחה שלכם עד עכשיו (קרא בעיון!):\n"
                for msg in recent_messages:
                    sender = "אתה (ליאור)" if msg['message_type'] == 'bot' else lead_data.get('name', 'הלקוח')
                    base_prompt += f"{sender}: {msg['content']}\n"
                base_prompt += "\n❗ חשוב: קראת את השיחה השלמה? אל תשאל שוב על דברים שהוא כבר אמר!\n"
        
        # Add current context
        base_prompt += f"\n\n📱 עכשיו {lead_data.get('name', 'הלקוח')} אמר לך: \"{user_message}\"\n"
        
        # Add what you know about them - comprehensive context
        context_info = self._build_human_context(lead_data, stage)
        if context_info:
            base_prompt += f"\n🧠 מה שאתה יודע עליו (חשוב! אל תשכח!):\n{context_info}\n"
            base_prompt += "\n⚠️ חובה: אם יש לך מידע עליו מכבר, אל תשאל שוב! תשתמש במידע הזה!\n"
        
        # Add specific guidance about what questions NOT to repeat
        if stage == 'collecting_profile':
            already_have = []
            if lead_data.get('rooms'): already_have.append("כמה חדרים")
            if lead_data.get('budget'): already_have.append("תקציב")
            if lead_data.get('has_parking') is not None: already_have.append("חניה")
            if lead_data.get('preferred_area'): already_have.append("אזור")
            
            if already_have:
                base_prompt += f"\n🚫 אל תשאל שוב על: {', '.join(already_have)}\n"
        
        # Context awareness without overly sensitive frustration detection
        # Let the AI naturally understand the conversation flow
        
        # Add current business context
        base_prompt += self._get_human_business_guidance(stage, lead_data)
        
        # Final human instructions
        base_prompt += """

             🎯 עכשיו ענה לו כמו בן אדם אמיתי:
             - אימוג'ים רק בסוף המשפטים, לא בהתחלה!
             - כל משפט בשורה נפרדת
             - תגיב ספציפית למה שהוא אמר
             - אל תישמע כמו רובוט עם תשובות מוכנות
             - אם אתה לא מבין משהו - תשאל הבהרה
             - אם אתה שמח/נפעם/מתרגש - תראה את זה!
             - זכור שאתה בן אדם עם אישיות
             - מקסימום 2 אימוג'ים בהודעה!
             - השאלה החשובה בבולד: **השאלה**
             
             עברית בלבד!"""
        
        return base_prompt
    
    # Removed frustration detection function - was too sensitive and causing issues

    def _build_human_context(self, lead_data: Dict, stage: str) -> str:
        """Build context in human, conversational way"""
        context_parts = []
        
        name = lead_data.get('name', 'הלקוח')
        if name and name != 'הלקוח':
            context_parts.append(f"השם שלו: {name}")
        
        # Business qualification info
        if lead_data.get('has_payslips') is True:
            context_parts.append("✅ יש לו תלושי שכר")
        elif lead_data.get('has_payslips') is False:
            context_parts.append("❌ אין לו תלושי שכר")
            
        if lead_data.get('can_pay_deposit') is True:
            context_parts.append("✅ יכול לשלם ערבות")
        elif lead_data.get('can_pay_deposit') is False:
            context_parts.append("❌ לא יכול לשלם ערבות")
            
        if lead_data.get('move_in_date'):
            context_parts.append(f"מועד כניסה: {lead_data.get('move_in_date')}")
        
        # Profile info
        if lead_data.get('rooms'):
            context_parts.append(f"מחפש {lead_data.get('rooms')} חדרים")
        if lead_data.get('budget'):
            context_parts.append(f"תקציב: {lead_data.get('budget'):,.0f} ש\"ח")
        if lead_data.get('has_parking') is True:
            context_parts.append("צריך חניה")
        elif lead_data.get('has_parking') is False:
            context_parts.append("לא צריך חניה")
        if lead_data.get('preferred_area'):
            context_parts.append(f"אזור מועדף: {lead_data.get('preferred_area')}")
        
        return "\n".join([f"- {part}" for part in context_parts]) if context_parts else ""
    
    def _get_missing_profile_fields_human(self, lead_data: Dict) -> List[str]:
        """Get human-readable list of missing profile fields"""
        missing = []
        if not lead_data.get('rooms'): missing.append("כמה חדרים")
        if not lead_data.get('budget'): missing.append("תקציב")
        if lead_data.get('has_parking') is None: missing.append("חניה")
        if not lead_data.get('preferred_area'): missing.append("אזור מועדף")
        return missing if missing else ["הכל יש!"]

    def _get_human_business_guidance(self, stage: str, lead_data: Dict) -> str:
        """Get guidance on what to focus on next, but in human way"""
        
        guidance_map = {
            'new': """
🎯 זה לקוח חדש! 
- תקבל אותו בחום 
- הציג את עצמך כליאור
- בצורה טבעית תשאל אם יש לו תלושי שכר (צריך את זה לביטוח)
- אל תזרוק עליו הכל בבת אחת!""",
            
            'gate_question_payslips': """
🎯 אתה מחכה לתשובה על תלושי שכר
- אם אמר שיש לו - תעבור לשאול על ערבות בצורה טבעית
- אם אמר שאין לו - תסביר בעדינות שזה נדרש
- אם לא הבנת - תשאל הבהרה""",
            
            'gate_question_deposit': """
🎯 אתה מחכה לתשובה על ערבות
- אם אמר שיכול לשלם - תעבור לשאול מתי הוא רוצה להיכנס
- אם אמר שלא יכול - תסביר בהבנה למה זה נדרש
- אם לא ברור - תשאל שוב בצורה ידידותית""",
            
            'gate_question_move_date': """
🎯 אתה מחכה לדעת מתי הוא רוצה להיכנס
- אם התאריך קרוב (עד 60 יום) - תתחיל לשאול על העדפות
- אם התאריך רחוק - תסביר שאתה עובד על תקופות קרובות יותר
- עבור לשאול כמה חדרים באופן טבעי""",
            
            'collecting_profile': f"""
🎯 אתה אוסף פרטים כדי למצוא לו דירה מושלמת
מה שחסר לדעת: {', '.join(self._get_missing_profile_fields_human(lead_data))}
- תשאל רק על דבר אחד בכל פעם בסדר הנכון: חדרים → תקציב → חניה → אזור
- תהיה סקרן ומעוניין באמת
- 🚨 חובה לשאול על תקציב בצורה ברורה: "מה התקציב החודשי שלך?" או "כמה אתה יכול להרשות לעצמך?"
- אל תשער תקציב מההודעות הקודמות - תמיד תשאל ישירות!
- אם נראה שיש לך מספיק מידע - תתרגש ותגיד "בוא אראה לך דירות!"
- אם יש לך הכל - תתרגש ותגיד שתחפש לו דירות!""",
            
            'qualified': """
🎯 הלקוח מוכשר! יש לך את כל המידע
- אם הוא שואל על דירות או מזכיר מקום - תציע לו לראות אפשרויות
- תהיה פרואקטיבי ומתלהב
- הזמן להראות לו דירות מתאימות!""",
            
            'scheduling_in_progress': """
🎯 הוא אמור לתאם פגישה בקלנדלי
- אם הוא אומר שתיאם - תתרגש ותאשר
- אם יש לו בעיות - תעזור לו
- תהיה תומך ועוזר""",
            
            'tour_scheduled': """
🎯 יש לכם פגישה מתוכננת! הכל מסודר!
- הפגישה כבר נקבעה בקלנדלי - הכל מאורגן
- ענה על שאלות על הפגישה בלבד (שעה, מיקום, הכנות)
- תהיה מתרגש לפגוש אותו אבל לא מוגזם
- אם הוא אומר תודה/thanks - פשוט תגיב בחיוביות קצרה
- 🚨 חשוב: אל תשאל שוב על תלושי שכר, ערבות, פרטים אישיים - הכל כבר נבדק ומסודר!
- אל תתייחס להודעות ישנות, רק להודעה הנוכחית
- תהיה מקצועי וקצר ולעניין""",

            'gate_failed': """
🎯 הוא לא עבר את הבדיקות, אבל אל תוותר
- תסביר בחום למה צריך את הדרישות
- תן לו תקווה לעתיד
- אם הוא משנה דעה עכשיו - תקבל את זה בשמחה!""",

            'future_fit': """
🎯 הוא רוצה לעבור רחוק מדי בעתיד
- תסביר שאתה מתמקד בתקופות קרובות
- תציע לחזור אליו יותר קרוב למועד
- תהיה חיובי למרות הפרידה""",

            'no_fit': """
🎯 לא מצאת לו דירות מתאימות
- תהיה כנה אבל עדיין מלא תקווה
- תציע אלטרנטיבות (תקציב/חדרים/אזור)
- תשאל אם הוא גמיש באיזשהו קריטריון"""
        }
        
        return guidance_map.get(stage, f"🎯 שלב {stage} - תענה בצורה טבעית ועוזרת")
    
    def _get_missing_profile_fields_human(self, lead_data: Dict) -> List[str]:
        """Get missing fields in human language"""
        missing = []
        if not lead_data.get('rooms'):
            missing.append("כמה חדרים")
        if not lead_data.get('budget'):
            missing.append("תקציב")
        if lead_data.get('has_parking') is None:
            missing.append("חניה")
        if not lead_data.get('preferred_area'):
            missing.append("אזור מועדף")
        return missing
    
    def _format_for_whatsapp(self, response: str) -> str:
        """Format response for WhatsApp with proper line breaks, emojis, and bold formatting"""
        
        # Clean up any unwanted AI artifacts but keep ** for bold
        response = response.replace("***", "**")  # Convert triple asterisks to double
        response = response.replace("בוט", "").replace("AI", "").replace("מערכת", "")
        
        # Ensure proper line breaks
        lines = response.split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if line:
                formatted_lines.append(line)
        
        # Join with proper spacing for WhatsApp
        formatted_response = '\n\n'.join(formatted_lines) if len(formatted_lines) > 1 else '\n'.join(formatted_lines)
        
        # Count emojis and limit to 2 max
        import re
        emoji_pattern = re.compile(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U0001F700-\U0001F77F\U0001F780-\U0001F7FF\U0001F800-\U0001F8FF\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002600-\U000027BF\U0001F004\U0001F0CF\U0001F170-\U0001F251]')
        emojis = emoji_pattern.findall(formatted_response)
        
        if len(emojis) > 2:
            # Remove excess emojis (keep first 2)
            for emoji in emojis[2:]:
                # Remove only the first occurrence of excess emojis
                formatted_response = formatted_response.replace(emoji, '', 1)
        
        # Make sure we have at least one emoji at the end if none exists
        remaining_emojis = emoji_pattern.findall(formatted_response)
        if not remaining_emojis:
            # Add a default friendly emoji at the end if none detected
            formatted_response = formatted_response + " 😊"
        
        return formatted_response.strip()
    
    def _build_human_property_recommendation_prompt(self, lead_data: Dict, properties: List[Dict]) -> str:
        """Build human-like property recommendation prompt"""
        
        prompt = f"""אתה ליאור, סוכן נדל"ן מתל אביב, וזה הרגע המרגש! מצאת דירות מושלמות עבור הלקוח.

🎉 הלקוח שלך חיפש:
- {lead_data.get('rooms')} חדרים
- תקציב עד {lead_data.get('budget'):,.0f} ש\"ח
- {'עם חניה' if lead_data.get('has_parking') else 'בלי חניה'}
- באזור: {lead_data.get('preferred_area', 'בכל תל אביב')}

🏠 והנה מה שמצאת בשבילו:"""
        
        for i, prop in enumerate(properties, 1):
            property_info = prop.get('properties', {}) if isinstance(prop.get('properties'), dict) else {}
            prompt += f"""

דירה {i}:
📍 {property_info.get('address', 'תל אביב')}
🏠 {prop.get('rooms')} חדרים | 💰 {prop.get('price'):,.0f} ש\"ח/חודש
🚗 {'חניה פרטית' if prop.get('has_parking') else 'ללא חניה'} | 📏 {prop.get('area_sqm', 'נ/א')} מ"ר | 🏢 קומה {prop.get('floor', 'נ/א')}"""
        
        prompt += f"""

             💭 עכשיו תגיב כליאור האמיתי:
             - תהיה מתרגש שמצאת משהו טוב!
             - אימוג'ים רק בסוף המשפטים, לא בהתחלה!
             - תכתוב בשורות נפרדות (כמו בווטסאפ)
             - תדגיש מה מיוחד בכל דירה בקשר לבקשות שלו
             - תסיים עם הצעה לתאם סיור באופן טבעי
             - תהיה אנושי, חם ומקצועי
             - מקסימום 2 אימוג'ים בכל ההודעה!
             - השאלה החשובה בבולד: **השאלה**
             - עברית בלבד!
             - הזכר שתשלח תמונות של הדירות מייד אחרי ההודעה!
             
             זכור: אתה לא רובוט! אתה ליאור שבאמת מתלהב כשמוצא דירה מושלמת ללקוח!"""
        
        return prompt
    
    def _build_human_no_properties_prompt(self, lead_data: Dict, conversation_history: List[Dict]) -> str:
        """Build human-like prompt for no properties found scenario"""
        
        prompt = f"""אתה ליאור, ויש לך בעיה קטנה. חיפשת דירות ללקוח שלך ולא מצאת משהו שמתאים בדיוק לבקשה שלו.

הוא רצה:
- {lead_data.get('rooms')} חדרים  
- עד {lead_data.get('budget'):,.0f} ש\"ח
- {'עם חניה' if lead_data.get('has_parking') else 'בלי חניה'}

אבל אין בזמן הזה דירות זמינות שמתאימות בדיוק.

             💭 עכשיו תגיב כליאור האמיתי:
             - תהיה קצר וישיר - מקסימום 4-5 שורות!
             - אימוג'ים רק בסוף המשפטים, לא בהתחלה!
             - תציע רק 2-3 אלטרנטיבות קצרות:
               * תקציב קצת גבוה יותר?
               * פחות חדרים?
               * בלי חניה?
             - תשאל איזה קריטריון הוא הכי גמיש בו
             - תהיה אופטימי אבל קצר!
             - מקסימום 2 אימוג'ים בהודעה!
             - השאלה בבולד: **השאלה**
             - עברית בלבד!
             
             זכור: קצר וחברותי, לא ארוך ומורכב!"""
        
        return prompt
    
    def generate_raw_response(self, prompt: str) -> str:
        """Generate raw AI response without any stage-specific formatting"""
        try:
            self._ensure_initialized()
            
            logger.info("Generating raw AI response")
            
            # Configure generation settings for more creative and human-like responses
            generation_config = types.GenerateContentConfig(
                temperature=1.2,
                top_p=0.95,
                top_k=40,
                max_output_tokens=400,
                safety_settings=[
                    types.SafetySetting(
                        category="HARM_CATEGORY_HARASSMENT",
                        threshold="BLOCK_ONLY_HIGH"
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_HATE_SPEECH", 
                        threshold="BLOCK_ONLY_HIGH"
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        threshold="BLOCK_ONLY_HIGH"
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_DANGEROUS_CONTENT",
                        threshold="BLOCK_ONLY_HIGH"
                    ),
                ],
# Note: ThinkingConfig may not be available in this version
                # thinking_config disabled for now
            )
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=generation_config
            )
            
            result = ""
            if hasattr(response, 'text') and response.text:
                result = response.text.strip()
            elif hasattr(response, 'candidates') and response.candidates:
                for candidate in response.candidates:
                    if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                        for part in candidate.content.parts:
                            if hasattr(part, 'text') and part.text:
                                result += part.text
                result = result.strip()
            
            logger.info(f"Raw AI response generated, length: {len(result)}")
            return result
            
        except Exception as e:
            logger.error(f"Error generating raw AI response: {e}")
            return ""


# Global Gemini service instance
gemini_service = GeminiService()