from client_base import BaseClient
from config import CLIENT_TYPES, EVENT_TYPES, PROTOCOL_MESSAGES
import logging

logger = logging.getLogger(__name__)

class ComputeClient(BaseClient):
    """Compute client for mathematical operations."""
    
    def __init__(self):
        super().__init__("ComputeProcessor", CLIENT_TYPES['COMPUTE'])
    
    def on_text_change(self, *args):
        """Handle text input changes for computations."""
        text = self.text_var.get()
        
        if len(text) > 0 and not self.is_typing:
            # Start computation input
            self.send_message(EVENT_TYPES['COMPUTING'], PROTOCOL_MESSAGES['TYPING_START'])
            self.is_typing = True
            logger.debug("Computation input started")
            
        elif len(text) == 0 and self.is_typing:
            # End computation input
            self.send_message(EVENT_TYPES['COMPUTING'], PROTOCOL_MESSAGES['TYPING_END'])
            self.is_typing = False
            logger.debug("Computation input ended")
    
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
            self.send_message(EVENT_TYPES['COMPUTING'], PROTOCOL_MESSAGES['TYPING_END'])
            self.is_typing = False
        
        # Send number for computation
        if temp_text:
            self.send_message(EVENT_TYPES['COMPUTING'], temp_text)
            logger.info(f"Number sent for computation: {temp_text}")

def main():
    """Main compute client startup function."""
    client = ComputeClient()
    client.run()

if __name__ == '__main__':
    main()