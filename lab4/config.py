# Lab4 configuration

# Named pipe settings
PIPE_NAME = r'\\.\pipe\logger'
PIPE_BUFFER_SIZE = 65536
MAX_CLIENTS = 255

# Database settings
DATABASE_PATH = 'logger.db'

# Client settings
STATUS_UPDATE_INTERVAL = 10  # seconds
PIPE_READ_BUFFER_SIZE = 4096

# Client types
CLIENT_TYPES = {
    'TEXT': 'Text',
    'COMPUTE': 'Compute'
}

# Event types
EVENT_TYPES = {
    'REGISTER': 'REGISTER',
    'ACTIVE': 'Active',
    'IDLE': 'Idle', 
    'STARTED': 'Started',
    'STOPPED': 'Stopped',
    'TYPING': 'Typing',
    'COMPUTING': 'Computing'
}

# Event categories for database
EVENT_CATEGORIES = {
    'STATUS': 'status',
    'ACTION': 'action',
    'RESULT': 'result'
}

# Protocol messages
PROTOCOL_MESSAGES = {
    'TYPING_START': 'Начало ввода',
    'TYPING_END': 'Конец ввода',
    'TEXT_INPUT_PREFIX': 'Введен текст \'',
    'EXIT_COMMAND': 'exit'
} 