import logging
import sys

def setup_logger(name: str = "server", log_file: str = "server.log") -> logging.Logger:
    """Configure a thread-safe logger."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Avoid adding multiple handlers if setup_logger is called multiple times
    if not logger.handlers:
        # File handler
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        
        # Standard format: [Timestamp] [Level] - [Message]
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
    return logger