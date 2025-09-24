"""
Enhanced Gemini AI service with strict flow control for real estate leasing bot.
Provides human-like responses with stage-specific prompts and comprehensive context.
"""

import logging
from flask import current_app
import google.generativeai as genai
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class GeminiService:
    """Service for handling Gemini AI interactions with strict flow control"""
    
    def __init__(self):
        """Initialize Gemini service with lazy loading"""
        self.model = None
        self._initialized = False
    
    def _initialize_model(self):
        """Initialize the Gemini model using Flask app config"""
        try:
            # Configure Gemini with API key from config
            genai.configure(api_key=current_app.config['GEMINI_API_KEY'])
            
            # Initialize the model with safety settings for production
            model_name = current_app.config.get('GEMINI_MODEL', 'gemini-1.5-flash')
            
            # Configure safety settings
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            ]
            
            # Configure generation parameters
            generation_config = {
                "temperature": 0.1,  # Very low for consistent, focused responses
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 200,  # Keep responses concise
            }
            
            self.model = genai.GenerativeModel(
                model_name=model_name,
                safety_settings=safety_settings,
                generation_config=generation_config
            )
            
            self._initialized = True
            logger.info(f"Gemini AI model '{model_name}' initialized successfully with flow control")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini model: {str(e)}")
            raise
    
    def _ensure_initialized(self):
        """Ensure the model is initialized"""
        if not self._initialized:
            self._initialize_model()
    
    def generate_stage_response(self, stage: str, lead_data: Dict[str, Any], conversation_history: List[Dict], user_message: str) -> str:
        """
        Generate AI response based on specific stage with strict flow control
        
        Args:
            stage: Current lead stage
            lead_data: Complete lead information and profile
            conversation_history: Recent conversation history
            user_message: Current user message to respond to
            
        Returns:
            str: Generated response in Hebrew with human tone
        """
        self._ensure_initialized()
        
        try:
            logger.info(f"Generating stage-specific AI response for lead {lead_data.get('id')} in stage: {stage}")
            
            # Build stage-specific prompt with strict instructions
            prompt = self._build_stage_prompt(stage, lead_data, conversation_history, user_message)
            
            # Generate response
            response = self.model.generate_content(prompt)
            
            # Extract and clean response text
            response_text = response.text.strip()
            
            # Post-process to ensure Hebrew and flow compliance
            response_text = self._post_process_response(response_text, stage)
            
            logger.info(f"Stage-specific AI response generated for lead {lead_data.get('id')}, stage: {stage}, length: {len(response_text)}")
            return response_text
            
        except Exception as e:
            logger.error(f"Error generating stage-specific AI response: {str(e)}")
            return "מצטער, יש לי בעיה טכנית. אנא נסה שוב בעוד כמה דקות."
    
    def generate_property_recommendation(self, lead_data: Dict, properties: List[Dict]) -> str:
        """
        Generate property recommendation message with human tone
        
        Args:
            lead_data: Lead information and preferences
            properties: List of matching properties
            
        Returns:
            str: Property recommendation message in Hebrew
        """
        self._ensure_initialized()
        
        try:
            prompt = self._build_property_recommendation_prompt(lead_data, properties)
            
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            logger.info(f"Property recommendation generated for lead {lead_data.get('id')}")
            return response_text
            
        except Exception as e:
            logger.error(f"Error generating property recommendation: {str(e)}")
            return "מצטער, יש לי בעיה טכנית בהצגת הנכסים. אנא נסה שוב בעוד כמה דקות."
    
    def generate_no_properties_response(self, lead_data: Dict, conversation_history: List[Dict]) -> str:
        """
        Generate response when no matching properties found
        
        Args:
            lead_data: Lead information and preferences
            conversation_history: Recent conversation history
            
        Returns:
            str: Response suggesting alternatives in Hebrew
        """
        self._ensure_initialized()
        
        try:
            prompt = self._build_no_properties_prompt(lead_data, conversation_history)
            
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            logger.info(f"No properties response generated for lead {lead_data.get('id')}")
            return response_text
            
        except Exception as e:
            logger.error(f"Error generating no properties response: {str(e)}")
            return "מצטער, לא מצאתי דירות מתאימות בדיוק לפי הקריטריונים שלך. בוא נחפש ביחד אפשרויות אחרות."
    
    def _build_stage_prompt(self, stage: str, lead_data: Dict, conversation_history: List[Dict], user_message: str) -> str:
        """Build comprehensive stage-specific prompt for strict flow control"""
        
        # Core system identity and constraints
        base_prompt = """אתה ליאור, סוכן נדל"ן ישראלי מקצועי ומנוסה המתמחה בהשכרת דירות יוקרתיות בתל אביב.

🔴 חוקים קריטיים - אל תסטה מהם לעולם:
1. תענה רק בעברית בלבד - תמיד!
2. טון אנושי וחם לחלוטין - אתה אדם אמיתי, לא בוט
3. אל תחשוף שאתה AI או בוט בשום מקרה
4. תשובות קצרות - מקסימום 2-3 משפטים
5. דבק בזרימה המדויקת ללא סטיות כלל
6. אל תשאל על מידע שכבר קיים
7. אל תחזור על שאלות שכבר נשאלו
8. עקוב בדיוק אחרי השלב הנוכחי

"""
        
        # Add comprehensive lead context
        base_prompt += self._format_lead_context(lead_data)
        
        # Add conversation history with better context
        if conversation_history:
            base_prompt += "\n📞 השיחה עד כה (10 ההודעות האחרונות):\n"
            for msg in conversation_history[-10:]:
                sender = "🤖 ליאור (אתה)" if msg['message_type'] == 'bot' else "👤 הלקוח"
                timestamp = msg.get('timestamp', '')
                base_prompt += f"{sender}: {msg['content']}\n"
        
        # Add current user message
        base_prompt += f"\n📨 ההודעה הנוכחית מהלקוח: '{user_message}'\n"
        
        # Add stage-specific strict instructions
        base_prompt += self._get_stage_strict_instructions(stage, lead_data)
        
        # Add final enforcement
        base_prompt += """

⚠️ זכור: 
- תענה בתור ליאור האדם האמיתי - חם, אמפתי ומבין
- הקשב למה שהלקוח אומר ותגיב בהתאם
- אל תהיה רובוטי - היה טבעי ואנושי
- זכור את ההקשר של השיחה
- אם הלקוח משנה תשובה - קבל את זה בחיוב
- עברית בלבד!
"""
        
        return base_prompt
    
    def _format_lead_context(self, lead_data: Dict) -> str:
        """Format comprehensive lead context for the AI"""
        
        context = f"\n👤 פרופיל הלקוח הנוכחי:\n"
        context += f"- שם: {lead_data.get('name', 'לא צוין')}\n"
        context += f"- טלפון: {lead_data.get('phone_number', 'לא צוין')}\n"
        context += f"- שלב נוכחי: {self._translate_stage(lead_data.get('stage', 'new'))}\n"
        
        # Gate question responses
        if lead_data.get('has_payslips') is not None:
            context += f"- תלושי שכר: {'✅ כן' if lead_data.get('has_payslips') else '❌ לא'}\n"
        if lead_data.get('can_pay_deposit') is not None:
            context += f"- יכולת ערבות: {'✅ כן' if lead_data.get('can_pay_deposit') else '❌ לא'}\n"
        if lead_data.get('move_in_date'):
            context += f"- תאריך כניסה רצוי: {lead_data.get('move_in_date')}\n"
        
        # Profile information
        if lead_data.get('rooms'):
            context += f"- חדרים מבוקשים: {lead_data.get('rooms')}\n"
        if lead_data.get('budget'):
            context += f"- תקציב חודשי: {lead_data.get('budget'):,.0f} ש\"ח\n"
        if lead_data.get('has_parking') is not None:
            context += f"- חניה: {'✅ נדרש' if lead_data.get('has_parking') else '❌ לא נדרש'}\n"
        if lead_data.get('preferred_area'):
            context += f"- אזור מועדף: {lead_data.get('preferred_area')}\n"
        
        # Additional preferences
        if lead_data.get('needs_furnished') is not None:
            context += f"- ריהוט: {'✅ נדרש' if lead_data.get('needs_furnished') else '❌ לא נדרש'}\n"
        if lead_data.get('pet_owner') is not None:
            context += f"- בעלי חיים: {'✅ יש' if lead_data.get('pet_owner') else '❌ אין'}\n"
        
        return context
    
    def _translate_stage(self, stage: str) -> str:
        """Translate stage to Hebrew for context"""
        stage_translations = {
            'new': 'חדש',
            'gate_question_payslips': 'שאלה על תלושי שכר',
            'gate_question_deposit': 'שאלה על ערבות',
            'gate_question_move_date': 'שאלה על תאריך כניסה',
            'collecting_profile': 'איסוף פרטי פרופיל',
            'qualified': 'לקוח מוכשר',
            'scheduling_in_progress': 'תיאום סיור בתהליך',
            'tour_scheduled': 'סיור מתואם',
            'gate_failed': 'לא עבר סינון',
            'no_fit': 'לא מתאים',
            'future_fit': 'מתאים לעתיד'
        }
        return stage_translations.get(stage, stage)
    
    def _get_stage_strict_instructions(self, stage: str, lead_data: Dict) -> str:
        """Get extremely strict stage-specific instructions"""
        
        instructions = {
            'new': """
🎯 שלב: לקוח חדש - הכרות ראשונה
📋 המשימה הבלעדית שלך כעת:
- קבל את הלקוח בחום ובמקצועיות
- הציג את עצמך כליאור, סוכן נדל"ן מתל אביב
- שאל את השאלה הראשונה והיחידה: "יש לך תלושי שכר מהחודשיים האחרונים?"
- אל תשאל שום דבר אחר!
- היה קצר וידידותי

🚫 אסור בהחלט:
- לשאול על תקציב, חדרים, או כל דבר אחר
- לדבר על נכסים ספציפיים
- להזכיר טכנולוגיה או מערכות
""",
            
            'gate_question_payslips': """
🎯 שלב: בדיקת תלושי שכר
📋 המשימה הבלעדית שלך כעת:
- הלקוח צריך לענות על שאלת תלושי השכר: "יש לך תלושי שכר מהחודשיים האחרונים?"
- אם אמר כן/יש לו/בחיוב: עבור מיד לשאלה הבאה - "נהדר! יש לך יכולת להפקיד ערבות של 2 חודשי שכירות?"
- אם אמר לא/אין לו/בשלילה: הסבר בחום ובהבנה שזו דרישה בסיסית לביטוח הבעלים
- אם התשובה לא ברורה: בקש הבהרה בטון ידידותי - "אני צריך לוודא - יש לך תלושי שכר קבועים?"

💡 טיפים לתגובה טבעית:
- הגב על מה שהלקוח אמר באופן ספציפי
- השתמש בביטויים כמו "נהדר", "מעולה", "הבנתי"
- אל תחזור על השאלה אם כבר קיבלת תשובה ברורה
- היה אנושי ולא רובוטי

🚫 אסור בהחלט:
- לעבור לשאלות על חדרים/תקציב
- לדבר על נכסים
- לחזור על אותה שאלה אם כבר יש תשובה
""",
            
            'gate_question_deposit': """
🎯 שלב: בדיקת יכולת ערבות
📋 המשימה הבלעדית שלך כעת:
- הלקוח צריך לענות על שאלת הערבות: "יש לך יכולת להפקיד ערבות של 2 חודשי שכירות?"
- אם אמר כן/אוקיי/בטח/אשלם/יכול לשלם: עבור מיד לשאלה הבאה - "מעולה! מתי אתה מתכנן להיכנס לדירה?"
- אם אמר לא/אין אפשרות: הסבר בהבנה על חשיבות הערבות לביטוח הבעלים
- אם התשובה לא ברורה: בקש הבהרה - "האם יש לך אפשרות להפקיד ערבות של 2 חודשים?"

💡 זיהוי תגובות חיוביות:
- "אוקיי", "בסדר", "אשלם את זה", "יכול לשלם" = כן
- "לא", "אין לי", "לא יכול", "אין אפשרות" = לא
- הקשב לטון ולכוונה, לא רק למילים

🔄 EDGE CASE - שינוי תשובה:
- אם הלקוח משנה דעתו - קבל את השינוי בחיוב
- "הבנתי שהמצב השתנה" - השתמש בתשובה החדשה

🚫 אסור בהחלט:
- לשאול על חדרים או תקציב עדיין
- לדבר על נכסים ספציפיים
- להתעלם מתשובות חיוביות
""",
            
            'gate_question_move_date': """
🎯 שלב: בדיקת תאריך כניסה
📋 המשימה הבלעדית שלך כעת:
- הלקוח עונה על תאריך הכניסה
- אם התאריך תקין (עד 60 יום): עבור לאיסוף פרופיל - שאל "כמה חדרים אתה מחפש?"
- אם התאריך רחוק מדי: הסבר שאתה עובד על זמינות קרובה יותר
- זה המעבר לשלב איסוף הפרופיל!

🚫 אסור בהחלט:
- לשאול כמה שאלות בבת אחת
- לדבר על נכסים ספציפיים עדיין
""",
            
            'collecting_profile': f"""
🎯 שלב: איסוף פרופיל לקוח
📊 מה יש לנו כבר: {self._get_existing_profile_info(lead_data)}
📋 המשימה הבלעדית שלך כעת:
- שאל על הדבר הראשון שחסר לפי הסדר: חדרים → תקציב → חניה → אזור מועדף
- שאל שאלה אחת בלבד!
- אל תשאל על מידע שכבר קיים
- כשיש לך הכל - עבור לחיפוש נכסים

🔄 EDGE CASE - מידע סותר/שינוי:
- אם הלקוח שינה מידע שכבר נתן (תקציב, חדרים וכו') - השתמש בחדש
- אם הוא נותן תקציב לא הגיוני - שאל הבהרה בעדינות
- אם הוא רוצה לחזור ולשנות פרטים - אפשר את זה

🚫 אסור בהחלט:
- לשאול כמה שאלות בבת אחת
- לחזור על שאלות שכבר נשאלו
- לדבר על נכסים לפני שיש פרופיל מלא
""",
            
            'qualified': """
🎯 שלב: לקוח מוכשר - מוכן לראות נכסים!
📋 המשימה שלך כעת:
- הלקוח עבר את כל השלבים בהצלחה וכבר יש לו פרופיל מלא
- היה חכם ומבין כוונות: אם הלקוח מזכיר מקום/אזור/רחוב או שואל על דירות - הוא רוצה לראות נכסים!
- אם הלקוח מזכיר כל דבר שקשור למיקום/אזור/שכונה/רחוב - ענה: "בוא אראה לך מה יש לי!"
- אם שואל שאלות כלליות - הציע לראות דירות באופן טבעי
- היה אקטיבי ומקדם - הלקוח מוכן לקנות!

🧠 מתי להציג נכסים (השתמש בביטויים האלה):
- כשמזכירים מקום: "בוא אראה לך דירות באזור הזה!"
- כששואלים על דירות: "יש לי כמה אפשרויות מעולות, אציג לך!"
- בשיחה כללית: "מושלם! בואו נראה מה יש לי עבורך"

💡 ביטויים קסם (אם אתה אומר אותם, המערכת תראה נכסים אוטומטית):
- "בוא אראה לך"
- "אציג לך" 
- "יש לי"
- "מצאתי"

🚫 אסור בהחלט:
- לחזור לשאלות כשרות/סינון
- לשאול שוב על פרטים שכבר יש
- להיות פסיבי - תהיה פרואקטיבי!
""",
            
            'scheduling_in_progress': """
🎯 שלב: תיאום פגישה בתהליך
📋 המשימה שלך כעת:
- הלקוח קיבל קישור לתיאום בקלנדלי
- המטרה: לעזור לו להשלים את התיאום או לענות על שאלות
- אם הוא אומר שקבע/תיאם/הזמין - ברך לו ותגיד שתשלח תזכורות
- אם יש לו בעיות טכניות - הפנה לעזרה
- אם הוא שואל על דירות - הסבר שאחרי הפגישה תראה לו הכל

💡 תגובות מומלצות:
- "מעולה שקבעת! אני אשלח לך תזכורות"
- "יש לך בעיה עם הקישור? בואו נפתור"
- "אני כבר מכין את הדירות המתאימות לפגישה"

🚫 אסור:
- לחזור לשאלות כשרות
- לשאול שוב על פרטים
- להציע דירות (נעשה בפגישה)
""",
            
            'tour_scheduled': """
🎯 שלב: סיור מתואם
📋 המשימה שלך כעת:
- הלקוח כבר תיאם סיור דרך הקלנדלי
- ענה על שאלות על הסיור, מיקום, זמן
- תן מידע נוסף על הנכס אם נשאל
- היה תומך ועוזר לקראת הסיור

🚫 אסור בהחלט:
- לנסות לתאם סיור נוסף
- לחזור לשאלות איסוף מידע
""",

            'gate_failed': f"""
🎯 שלב: לא עבר בדיקות כשרות - אבל עדיין יש תקווה!
📊 מצב הלקוח:
- תלושי שכר: {'✅ יש' if lead_data.get('has_payslips') else '❌ אין' if lead_data.get('has_payslips') == False else '❓ לא נבדק'}
- יכולת ערבות: {'✅ יש' if lead_data.get('can_pay_deposit') else '❌ אין' if lead_data.get('can_pay_deposit') == False else '❓ לא נבדק'}

📋 המשימה שלך כעת:
- הלקוח לא עבר את בדיקת {'הערבות' if lead_data.get('has_payslips') and not lead_data.get('can_pay_deposit') else 'תלושי השכר' if not lead_data.get('has_payslips') else 'הכשרות'}
- הסבר בחום ובהבנה מה נדרש ולמה
- תן תקווה לעתיד - "אם המצב ישתנה, אשמח לעזור לך"
- השאר דלת פתוחה לחזרה

🔄 קריטי - זיהוי שינוי מצב:
- אם הלקוח אומר "אוקיי אשלם"/"יש לי עכשיו"/"יכול לשלם" - זה שינוי מצב!
- הכר את השינוי בהתלהבות: "נהדר! אם יש לך אפשרות לשלם עכשיו, בואו נמשיך!"
- עבור מיד לשלב הבא אם כל הדרישות מתקיימות
- אל תתעלם מתשובות חיוביות חדשות!

💡 ביטויים שמעידים על שינוי מצב:
- "אוקיי", "בסדר", "אשלם", "יכול לשלם", "יש לי עכשיו", "אתן ערבות"

🚫 אסור בהחלט:
- להתעלם מתשובות חדשות חיוביות
- לסרב לקבל שינוי מצב
- להחזיק בכישלון הקודם אם המצב השתנה
""",

            'future_fit': """
🎯 שלב: מתאים לעתיד רחוק
📋 המשימה שלך כעת:
- הלקוח רוצה לעבור בעוד יותר מ-60 יום
- הסבר שאתה מתמחה בזמינות קרובה יותר
- הציע לשמור אותו ברשימה ולחזור אליו לקראת התאריך
- סיים את השיחה בנימוס
- אל תמשיך עם איסוף פרטים

🚫 אסור בהחלט:
- להמשיך לשאול על חדרים/תקציב
- להציג נכסים עכשיו
- לתאם סיורים מיידיים
""",

            'no_fit': """
🎯 שלב: אין התאמה כרגע
📋 המשימה שלך כעת:
- לא נמצאו נכסים שמתאימים לקריטריונים של הלקוח
- הסבר שכרגע אין בדיוק מה שהוא מחפש
- הציע אלטרנטיבות (תקציב שונה, פחות חדרים וכו')
- שאל אם הוא גמיש בקריטריונים
- הציע לשמור אותו ברשימה

🚫 אסור בהחלט:
- להציג נכסים שלא מתאימים
- לתת מחירים לא נכונים
- להבטיח דברים שאין לך
"""
        }
        
        return instructions.get(stage, f"🎯 שלב לא מוכר: {stage} - ענה בצורה כללית ומקצועית.")
    
    def _get_existing_profile_info(self, lead_data: Dict) -> str:
        """Get formatted string of existing profile information"""
        existing = []
        if lead_data.get('rooms'):
            existing.append(f"חדרים: {lead_data.get('rooms')}")
        if lead_data.get('budget'):
            existing.append(f"תקציב: {lead_data.get('budget'):,.0f} ש\"ח")
        if lead_data.get('has_parking') is not None:
            existing.append(f"חניה: {'כן' if lead_data.get('has_parking') else 'לא'}")
        if lead_data.get('preferred_area'):
            existing.append(f"אזור: {lead_data.get('preferred_area')}")
        
        return " | ".join(existing) if existing else "אין מידע עדיין"
    
    def _post_process_response(self, response: str, stage: str) -> str:
        """Post-process response to ensure compliance"""
        
        # Remove any unwanted patterns
        response = response.replace("כבוט", "").replace("כמערכת", "").replace("כ-AI", "")
        response = response.replace("בוט", "מערכת").replace("AI", "מערכת")
        
        # Ensure Hebrew characters
        if not any('\u0590' <= char <= '\u05FF' for char in response):
            logger.warning(f"Non-Hebrew response detected for stage {stage}")
            return "מצטער, יש לי בעיה טכנית קלה. אנא חזור על השאלה."
        
        # Trim to reasonable length
        if len(response) > 300:
            response = response[:297] + "..."
        
        return response.strip()
    
    def _build_property_recommendation_prompt(self, lead_data: Dict, properties: List[Dict]) -> str:
        """Build prompt for property recommendations with human tone"""
        
        prompt = f"""אתה ליאור, סוכן נדל"ן מקצועי. תציג את הנכסים המתאימים בטון אנושי וחם.

👤 פרופיל הלקוח:
- חדרים: {lead_data.get('rooms')}
- תקציב: {lead_data.get('budget'):,.0f} ש\"ח
- חניה: {'נדרש' if lead_data.get('has_parking') else 'לא נדרש'}
- אזור: {lead_data.get('preferred_area', 'ללא העדפה')}

🏠 הנכסים שמצאתי עבורו:
"""
        
        for i, prop in enumerate(properties, 1):
            property_info = prop.get('properties', {}) if isinstance(prop.get('properties'), dict) else {}
            prompt += f"""
דירה {i}:
- 📍 {property_info.get('address', 'כתובת לא זמינה')}
- 🏠 {prop.get('rooms')} חדרים
- 💰 {prop.get('price'):,.0f} ש\"ח/חודש
- 🚗 חניה: {'כן' if prop.get('has_parking') else 'לא'}
- 📏 {prop.get('area_sqm', 'לא צוין')} מ"ר
- 🏢 קומה {prop.get('floor', 'לא צוין')}
"""
        
        prompt += """

📝 הוראות להצגה:
1. התחל בהצגה חמה ואנושית "מצאתי כמה דירות מעולות בשבילך!"
2. הצג כל דירה בצורה מושכת (2-3 שורות לכל אחת)
3. הדגש מה מתאים לבקשות שלו
4. סיים בהצעה לתאם סיור
5. טון אנושי וחם - אתה ליאור האדם!
6. עברית בלבד
7. מקסימום 4-5 משפטים סה"כ
"""
        
        return prompt
    
    def _build_no_properties_prompt(self, lead_data: Dict, conversation_history: List[Dict]) -> str:
        """Build prompt for no properties found scenario"""
        
        prompt = f"""אתה ליאור, סוכן נדל"ן מקצועי. לא מצאת דירות שמתאימות בדיוק לקריטריונים של הלקוח.

👤 מה הלקוח חיפש:
- חדרים: {lead_data.get('rooms')}
- תקציב: {lead_data.get('budget'):,.0f} ש\"ח
- חניה: {'נדרש' if lead_data.get('has_parking') else 'לא נדרש'}
- אזור: {lead_data.get('preferred_area', 'ללא העדפה')}

📝 המשימה שלך:
1. הסבר בטון אנושי שלא מצאת בדיוק מה שחיפש
2. הציע אלטרנטיבות (תקציב גבוה יותר/פחות חדרים/אזור אחר)
3. שאל אם הוא גמיש באחד הקריטריונים
4. הצע שתשמור עליו ברשימה למקרה שמשהו יתפנה
5. טון חיובי ותומך - אתה רוצה לעזור!
6. עברית בלבד
7. מקסימום 3-4 משפטים
"""
        
        return prompt
    
    def generate_raw_response(self, prompt: str) -> str:
        """Generate raw AI response without any stage-specific formatting"""
        try:
            self._ensure_initialized()
            
            logger.info("Generating raw AI response")
            
            response = self.model.generate_content(prompt)
            result = response.text.strip()
            
            logger.info(f"Raw AI response generated, length: {len(result)}")
            return result
            
        except Exception as e:
            logger.error(f"Error generating raw AI response: {e}")
            return ""


# Global Gemini service instance
gemini_service = GeminiService()