import asyncio
import json
import websockets
from typing import Optional, Dict, Any, Callable
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class YellowWebSocketClient:
    """
    Real-time WebSocket client for Yellow Network ClearNode
    Based on official Yellow SDK documentation
    """
    
    def __init__(self, endpoint: str, app_id: str, api_key: str):
        self.endpoint = endpoint
        self.app_id = app_id
        self.api_key = api_key
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.is_connected = False
        self.message_handlers: Dict[str, Callable] = {}
        self.pending_requests: Dict[str, asyncio.Future] = {}
        self.request_id_counter = 0
        
    async def connect(self) -> bool:
        """Connect to Yellow Network ClearNode"""
        try:
            logger.info(f"Connecting to Yellow Network: {self.endpoint}")
            self.websocket = await websockets.connect(
                self.endpoint,
                extra_headers={
                    "X-Yellow-App-Id": self.app_id,
                    "X-Yellow-API-Key": self.api_key
                }
            )
            self.is_connected = True
            logger.info("✅ Connected to Yellow Network!")
            
            asyncio.create_task(self._message_listener())
            
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Yellow Network: {e}")
            self.is_connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from Yellow Network"""
        if self.websocket:
            await self.websocket.close()
            self.is_connected = False
            logger.info("Disconnected from Yellow Network")
    
    async def _message_listener(self):
        """Listen for incoming messages from Yellow Network"""
        try:
            async for message in self.websocket:
                await self._handle_message(message)
        except websockets.exceptions.ConnectionClosed:
            logger.warning("Connection to Yellow Network closed")
            self.is_connected = False
        except Exception as e:
            logger.error(f"Error in message listener: {e}")
            self.is_connected = False
    
    async def _handle_message(self, raw_message: str):
        """Parse and handle incoming messages"""
        try:
            message = json.loads(raw_message)
            logger.info(f"📨 Received: {message.get('type', 'unknown')}")
            
            message_type = message.get('type')
            request_id = message.get('id')
            
            if request_id and request_id in self.pending_requests:
                self.pending_requests[request_id].set_result(message)
                del self.pending_requests[request_id]
            
            if message_type in self.message_handlers:
                await self.message_handlers[message_type](message)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse message: {e}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    def on(self, message_type: str, handler: Callable):
        """Register a message handler"""
        self.message_handlers[message_type] = handler
    
    async def send_rpc(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send RPC request and wait for response"""
        if not self.is_connected or not self.websocket:
            raise ConnectionError("Not connected to Yellow Network")
        
        self.request_id_counter += 1
        request_id = str(self.request_id_counter)
        
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {}
        }
        
        future = asyncio.Future()
        self.pending_requests[request_id] = future
        
        await self.websocket.send(json.dumps(request))
        logger.info(f"📤 Sent RPC: {method}")
        
        try:
            response = await asyncio.wait_for(future, timeout=30.0)
            return response
        except asyncio.TimeoutError:
            if request_id in self.pending_requests:
                del self.pending_requests[request_id]
            raise TimeoutError(f"RPC request {method} timed out")
    
    async def create_session(
        self,
        user_address: str,
        partner_address: str,
        user_allocation: int,
        partner_allocation: int,
        asset: str = "usdc"
    ) -> Dict[str, Any]:
        """
        Create a Yellow Network application session
        Based on Yellow SDK createAppSessionMessage
        """
        app_definition = {
            "protocol": "payment-app-v1",
            "participants": [user_address, partner_address],
            "weights": [50, 50],
            "quorum": 100,
            "challenge": 0,
            "nonce": int(datetime.utcnow().timestamp() * 1000)
        }
        
        allocations = [
            {
                "participant": user_address,
                "asset": asset,
                "amount": str(user_allocation)
            },
            {
                "participant": partner_address,
                "asset": asset,
                "amount": str(partner_allocation)
            }
        ]
        
        session_data = {
            "definition": app_definition,
            "allocations": allocations
        }
        
        response = await self.send_rpc(
            method="app.createSession",
            params=session_data
        )
        
        return response
    
    async def submit_order(
        self,
        session_id: str,
        order_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Submit an order through the state channel"""
        response = await self.send_rpc(
            method="app.submitOrder",
            params={
                "sessionId": session_id,
                "order": order_data
            }
        )
        
        return response
    
    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get order status"""
        response = await self.send_rpc(
            method="app.getOrderStatus",
            params={"orderId": order_id}
        )
        
        return response
    
    async def send_payment(
        self,
        session_id: str,
        amount: int,
        recipient: str
    ) -> Dict[str, Any]:
        """Send instant payment through state channel"""
        payment_data = {
            "sessionId": session_id,
            "type": "payment",
            "amount": str(amount),
            "recipient": recipient,
            "timestamp": int(datetime.utcnow().timestamp() * 1000)
        }
        
        response = await self.send_rpc(
            method="app.sendPayment",
            params=payment_data
        )
        
        return response
    
    async def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """Get session information"""
        response = await self.send_rpc(
            method="app.getSession",
            params={"sessionId": session_id}
        )
        
        return response
    
    async def close_session(self, session_id: str) -> Dict[str, Any]:
        """Close a session and settle on-chain"""
        response = await self.send_rpc(
            method="app.closeSession",
            params={"sessionId": session_id}
        )
        
        return response


class YellowWebSocketManager:
    """
    Manager for Yellow WebSocket connections
    Maintains connection pool and handles reconnection
    """
    
    def __init__(self):
        self.clients: Dict[str, YellowWebSocketClient] = {}
        self.default_client: Optional[YellowWebSocketClient] = None
    
    async def get_client(
        self,
        endpoint: str,
        app_id: str,
        api_key: str
    ) -> YellowWebSocketClient:
        """Get or create a WebSocket client"""
        client_key = f"{endpoint}:{app_id}"
        
        if client_key in self.clients and self.clients[client_key].is_connected:
            return self.clients[client_key]
        
        client = YellowWebSocketClient(endpoint, app_id, api_key)
        await client.connect()
        
        self.clients[client_key] = client
        
        if self.default_client is None:
            self.default_client = client
        
        return client
    
    async def close_all(self):
        """Close all WebSocket connections"""
        for client in self.clients.values():
            await client.disconnect()
        self.clients.clear()
        self.default_client = None


yellow_ws_manager = YellowWebSocketManager()
