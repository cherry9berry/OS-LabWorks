import win32pipe
import win32file
import pywintypes
import threading
import logging
from datetime import datetime
from database_manager import DatabaseManager
from event_processor import EventProcessor
from config import (PIPE_NAME, PIPE_BUFFER_SIZE, MAX_CLIENTS, PIPE_READ_BUFFER_SIZE,
                   EVENT_TYPES)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LoggerServer:
    """Server for logging client data via named pipes."""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.event_processor = EventProcessor()
        self.client_counter = 1
        
    def handle_client(self, pipe, client_id):
        """Handle connected client."""
        try:
            # Wait for REGISTER message
            data = win32file.ReadFile(pipe, PIPE_READ_BUFFER_SIZE)[1].decode()
            if not data.startswith(f"{EVENT_TYPES['REGISTER']}:"):
                logger.error(f"[{client_id}] Error: Expected REGISTER message, got: {data}")
                return
            
            # Parse registration
            try:
                _, base_name, client_type = data.split(':')
            except ValueError:
                logger.error(f"[{client_id}] Invalid REGISTER message format: {data}")
                return
            
            # Register client in database
            client_name = self.db_manager.register_client(base_name, client_type)
            
            # Send client unique name and client_id
            response = f"NAME:{client_name}:{client_id}"
            win32file.WriteFile(pipe, response.encode())
            
            logger.info(f"[{client_id}] Client {client_name} ({client_type}) connected")
            
            # Main message processing loop
            while True:
                data = win32file.ReadFile(pipe, PIPE_READ_BUFFER_SIZE)[1].decode()
                self._process_client_message(data, client_id, client_type)
                
        except pywintypes.error as e:
            if e.args[0] == 109:  # Pipe closed
                logger.info(f"[{client_id}] Client disconnected")
            else:
                logger.error(f"[{client_id}] Pipe error: {e}")
        except Exception as e:
            logger.error(f"[{client_id}] Unexpected error: {e}")
        finally:
            try:
                win32file.CloseHandle(pipe)
            except:
                pass
    
    def _process_client_message(self, data, client_id, client_type):
        """Process client message."""
        try:
            event_type, details = data.split(':', 1)
        except ValueError:
            logger.warning(f"[{client_id}] Invalid message format: {data}")
            return
        
        # Process event via EventProcessor
        event_category, processed_details = self.event_processor.process_event(event_type, details)
        
        # Save to database
        self.db_manager.save_event(client_id, client_type, event_category, processed_details)
        
        # Console logging
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        console_message = f"[{timestamp}] [{client_id}] [{client_type}] {event_category}: {processed_details}"
        print(console_message)
        logger.info(f"[{client_id}] Processed event: {event_type} -> {event_category}: {processed_details}")
    
    def create_named_pipe(self):
        """Create named pipe."""
        try:
            pipe = win32pipe.CreateNamedPipe(
                PIPE_NAME,
                win32pipe.PIPE_ACCESS_DUPLEX,
                win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | win32pipe.PIPE_WAIT,
                MAX_CLIENTS, 
                PIPE_BUFFER_SIZE, 
                PIPE_BUFFER_SIZE, 
                0, 
                None
            )
            return pipe
        except pywintypes.error as e:
            logger.error(f"Named pipe creation error: {e}")
            return None
    
    def start_server(self):
        """Start server."""
        logger.info("Starting logging server...")
        print("Server started. Waiting for client connections...")
        
        while True:
            try:
                # Create named pipe
                pipe = self.create_named_pipe()
                if pipe is None:
                    logger.error("Failed to create named pipe")
                    break
                
                # Wait for client connection
                logger.debug("Waiting for client connection...")
                win32pipe.ConnectNamedPipe(pipe, None)
                
                # Start client handler in separate thread
                client_thread = threading.Thread(
                    target=self.handle_client, 
                    args=(pipe, self.client_counter),
                    daemon=True
                )
                client_thread.start()
                
                self.client_counter += 1
                
            except KeyboardInterrupt:
                logger.info("Shutdown signal received. Stopping server...")
                break
            except Exception as e:
                logger.error(f"Server main loop error: {e}")
                continue

def main():
    """Main server startup function."""
    server = LoggerServer()
    try:
        server.start_server()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Critical server error: {e}")

if __name__ == '__main__':
    print("Запуск сервера...")
    main()