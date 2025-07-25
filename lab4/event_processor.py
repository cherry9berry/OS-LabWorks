import logging
from config import EVENT_TYPES, EVENT_CATEGORIES, PROTOCOL_MESSAGES

logger = logging.getLogger(__name__)

class EventProcessor:
    """Event processor for client message categorization and handling."""
    
    @staticmethod
    def process_event(event_type, details):
        """Process event and determine its category."""
        if event_type in (EVENT_TYPES['ACTIVE'], EVENT_TYPES['IDLE']):
            return EVENT_CATEGORIES['STATUS'], event_type
        
        elif event_type == EVENT_TYPES['STARTED']:
            return EVENT_CATEGORIES['ACTION'], "Started"
        
        elif event_type == EVENT_TYPES['STOPPED']:
            return EVENT_CATEGORIES['ACTION'], "Finished"
        
        elif event_type in (EVENT_TYPES['TYPING'], EVENT_TYPES['COMPUTING']):
            if details in (PROTOCOL_MESSAGES['TYPING_START'], PROTOCOL_MESSAGES['TYPING_END']):
                action = "Typing started" if details == PROTOCOL_MESSAGES['TYPING_START'] else "Typing ended"
                return EVENT_CATEGORIES['ACTION'], action
            else:
                # Process results
                return EventProcessor._process_result_event(event_type, details)
        
        else:
            logger.warning(f"Unknown event type: {event_type}")
            return EVENT_CATEGORIES['RESULT'], details
    
    @staticmethod
    def _process_result_event(event_type, details):
        """Process result events."""
        if event_type == EVENT_TYPES['TYPING']:
            # Extract text from "Введен текст 'text'"
            if details.startswith(PROTOCOL_MESSAGES['TEXT_INPUT_PREFIX']):
                try:
                    text = details.split("'")[1]
                    return EVENT_CATEGORIES['RESULT'], text
                except IndexError:
                    logger.warning(f"Failed to extract text from: {details}")
                    return EVENT_CATEGORIES['RESULT'], details
            else:
                return EVENT_CATEGORIES['RESULT'], details
        
        elif event_type == EVENT_TYPES['COMPUTING']:
            # Compute square of number
            result = EventProcessor._compute_square(details)
            return EVENT_CATEGORIES['RESULT'], result
        
        return EVENT_CATEGORIES['RESULT'], details
    
    @staticmethod
    def _compute_square(text):
        """Compute square of number."""
        try:
            num = float(text)
            result = str(num ** 2)
            logger.debug(f"Computed square: {text} -> {result}")
            return result
        except ValueError:
            logger.warning(f"Cannot compute square for: {text}")
            return "-1" 