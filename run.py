#!/usr/bin/env python3
"""
Standalone script to run the Snake Classic Notification Backend.
This script can be used to start the server directly.
"""

import os
import sys
import logging
import uvicorn

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

def main():
    """Main entry point for the application."""
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    logger = logging.getLogger(__name__)
    
    logger.info("🐍 Starting Snake Classic Notification Backend")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Host: {settings.api_host}")
    logger.info(f"Port: {settings.api_port}")
    logger.info(f"Firebase Project: {settings.firebase_project_id}")
    
    try:
        # Run the application
        uvicorn.run(
            "app.main:app",
            host=settings.api_host,
            port=settings.api_port,
            reload=settings.api_reload and settings.is_development,
            log_level=settings.log_level.lower(),
            access_log=True
        )
    
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Failed to start server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()