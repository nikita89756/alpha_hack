"""Application configuration"""
import os
from functools import lru_cache


class Config:

    
    def __init__(self):

        self.DEBUG = os.getenv("DEBUG", "False").lower() == "true"

        self.MESSAGE_SERVICE_URL = os.getenv("MESSAGE_SERVICE_URL", "http://message-service:8001")
        self.WS_SERVICE_URL = os.getenv("WS_SERVICE_URL", "http://ws-service:8002")
        self.AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8004")
        self.BOT_SERVICE_URL = os.getenv("BOT_SERVICE_URL", "http://bot-service:8003")
        self.IMAGE_ANALYSIS_SERVICE_URL: str = "http://analyze-service:8005"
        self.BUSINESS_SERVICE_URL=os.getenv("BUSINESS_SERVICE_URL","http://business-service:8007")
        self.CALENDAR_SERVICE_URL=os.getenv("CALENDAR_SERVICE_URL","http://calendar-service:8008")
        self.REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "120.0"))
        self.DOCUMENT_PARSER_SERVICE_URL: str=os.getenv("DOCUMENT_PARSER_SERVICE_URL","http://document-parser-service:8006")
        self.WB_SERVICE_URL = os.getenv("WB_SERVICE_URL","http://wb-pnl-service:8009")
        
        cors_origins = os.getenv("CORS_ORIGINS", "*")
        self.CORS_ORIGINS = [origin.strip() for origin in cors_origins.split(",")]
        
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


@lru_cache()
def get_config() -> Config:
    return Config()
