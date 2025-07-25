import sqlite3
import os
import logging
from datetime import datetime
from config import DATABASE_PATH

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Database manager for client event logging."""
    
    def __init__(self, db_path=DATABASE_PATH, recreate_db=True):
        self.db_path = db_path
        self.setup_database(recreate_db)
    
    def setup_database(self, recreate=True):
        """Setup database tables."""
        if recreate and os.path.exists(self.db_path):
            os.remove(self.db_path)
            logger.info(f"Existing database {self.db_path} removed.")
        
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            
            # Create clients table
            cur.execute('''CREATE TABLE IF NOT EXISTS clients (
                            client_id INTEGER PRIMARY KEY AUTOINCREMENT,
                            client_name TEXT UNIQUE,
                            client_type TEXT)''')
            
            # Create events table
            cur.execute('''CREATE TABLE IF NOT EXISTS events (
                            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                            timestamp TEXT,
                            client_id INTEGER,
                            client_type TEXT,
                            event_category TEXT,
                            event_value TEXT,
                            FOREIGN KEY(client_id) REFERENCES clients(client_id))''')
            
            conn.commit()
        
        logger.info(f"Database {self.db_path} configured.")
    
    def register_client(self, base_name, client_type):
        """Register new client in database."""
        client_id = 1
        while True:
            client_name = f"{base_name}_{client_id}"
            try:
                with sqlite3.connect(self.db_path, timeout=10) as conn:
                    cur = conn.cursor()
                    cur.execute('INSERT INTO clients (client_name, client_type) VALUES (?, ?)',
                                (client_name, client_type))
                    conn.commit()
                    logger.info(f"Client {client_name} registered with type {client_type}")
                    return client_name
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e):
                    import time
                    time.sleep(0.1)
                    continue
                raise e
            except sqlite3.IntegrityError:
                client_id += 1
    
    def save_event(self, client_id, client_type, event_category, event_value):
        """Save event to database."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with sqlite3.connect(self.db_path, timeout=10) as conn:
                cur = conn.cursor()
                cur.execute('''INSERT INTO events 
                              (timestamp, client_id, client_type, event_category, event_value) 
                              VALUES (?, ?, ?, ?, ?)''',
                            (timestamp, client_id, client_type, event_category, event_value))
                conn.commit()
                logger.debug(f"Event saved: [{client_id}] [{client_type}] {event_category}: {event_value}")
        except sqlite3.Error as e:
            logger.error(f"Event save error: {e}") 