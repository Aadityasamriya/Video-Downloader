"""
Simple health check server for Railway deployment monitoring
"""
import asyncio
import logging
from aiohttp import web
import threading

logger = logging.getLogger(__name__)

class HealthServer:
    def __init__(self, port=8000):
        self.port = port
        self.app = web.Application()
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_get('/', self.health_check)
        
    async def health_check(self, request):
        """Health check endpoint"""
        return web.json_response({
            "status": "healthy",
            "service": "telegram-video-bot",
            "timestamp": str(asyncio.get_event_loop().time())
        })
    
    async def start_server(self):
        """Start health check server"""
        try:
            runner = web.AppRunner(self.app)
            await runner.setup()
            site = web.TCPSite(runner, '0.0.0.0', self.port)
            await site.start()
            logger.info(f"Health check server started on port {self.port}")
        except Exception as e:
            logger.error(f"Failed to start health server: {e}")

def start_health_server():
    """Start health server in background thread"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        health_server = HealthServer()
        loop.run_until_complete(health_server.start_server())
        loop.run_forever()
    except Exception as e:
        logger.error(f"Health server error: {e}")