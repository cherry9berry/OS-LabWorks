from client_base import BaseClient
from config import CLIENT_TYPES, EVENT_TYPES, PROTOCOL_MESSAGES
import logging

logger = logging.getLogger(__name__)

class TextClient(BaseClient):
    """Text client for text input processing."""
    
    def __init__(self):
        super().__init__("TextProcessor", CLIENT_TYPES['TEXT'])
    
    def on_text_change(self, *args):
        """Handle text input changes."""
        text = self.text_var.get()
        
        if len(text) > 0 and not self.is_typing:
            # Start typing
            self.send_message(EVENT_TYPES['TYPING'], PROTOCOL_MESSAGES['TYPING_START'])
            self.is_typing = True
            logger.debug("Text input started")
            
        elif len(text) == 0 and self.is_typing:
            # End typing
            self.send_message(EVENT_TYPES['TYPING'], PROTOCOL_MESSAGES['TYPING_END'])
            self.is_typing = False
            logger.debug("Text input ended")
    
    def on_send(self):
        """Handle send button click."""
        text = self.text_var.get()
        
        # Check exit command
        if text.lower() == PROTOCOL_MESSAGES['EXIT_COMMAND']:
            logger.info("Exit command received")
            self.on_closing()
            return
        
        # Save text and clear field
        temp_text = text
        self.text_var.set("")
        
        # Send end typing if was active
        if self.is_typing:
            self.send_message(EVENT_TYPES['TYPING'], PROTOCOL_MESSAGES['TYPING_END'])
            self.is_typing = False
        
        # Send entered text
        if temp_text:
            text_message = f"{PROTOCOL_MESSAGES['TEXT_INPUT_PREFIX']}{temp_text}'"
            self.send_message(EVENT_TYPES['TYPING'], text_message)
            logger.info(f"Text sent: {temp_text}")

def main():
    """Main text client startup function."""
    client = TextClient()
    client.run()

if __name__ == '__main__':
    main()