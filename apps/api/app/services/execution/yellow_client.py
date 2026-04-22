import asyncio
import logging
from typing import Optional, Dict, Any
from app.core.config import settings
from app.services.execution.yellow_websocket_client import yellow_ws_manager, YellowWebSocketClient

logger = logging.getLogger(__name__)


class YellowClient:
    def __init__(self):
        self.ws_url = "wss://clearnet-sandbox.yellow.com/ws"
        self.app_id = settings.yellow_app_id
        self.api_key = settings.yellow_api_key
        self.protocol = "payment-app-v1"
        self._ws_client: Optional[YellowWebSocketClient] = None
        self._connection_lock = asyncio.Lock()

    async def _get_ws_client(self) -> YellowWebSocketClient:
        async with self._connection_lock:
            if self._ws_client is None or not self._ws_client.is_connected:
                logger.info("Creating new Yellow WebSocket connection...")
                self._ws_client = await yellow_ws_manager.get_client(
                    endpoint=self.ws_url,
                    app_id=self.app_id,
                    api_key=self.api_key,
                )
            return self._ws_client

    async def create_session(self, wallet: str, session_key: str) -> Dict[str, Any]:
        try:
            ws_client = await self._get_ws_client()
            response = await ws_client.send_rpc(
                method="app.createSession",
                params={"wallet": wallet, "sessionKey": session_key},
            )
            if response.get("error"):
                logger.error("Yellow createSession error: %s", response["error"])
                return {
                    "error": response["error"],
                    "status": "FAILED",
                    "mode": "error",
                    "message": "Failed to create session on Yellow Network",
                }
            result = response.get("result", {})
            logger.info("Yellow session created for wallet=%s", wallet)
            return {
                "session_id": result.get("sessionId", f"yellow_session_{session_key}"),
                "wallet": wallet,
                "session_key": session_key,
                "status": "ACTIVE",
                "app_id": self.app_id,
                "protocol": self.protocol,
                "endpoint": self.ws_url,
                "yellow_response": result,
                "message": "Yellow Network session ready",
            }
        except Exception as exc:
            logger.error("Yellow createSession failed: %s", exc)
            return {
                "error": "yellow_network_unavailable",
                "status": "FAILED",
                "mode": "error",
                "message": f"Failed to create session on Yellow Network: {exc}",
            }

    async def validate_session(self, session_key: str, wallet: str) -> Dict[str, Any]:
        try:
            ws_client = await self._get_ws_client()
            response = await ws_client.send_rpc(
                method="app.validateSession",
                params={"sessionKey": session_key, "wallet": wallet},
            )
            if response.get("error"):
                logger.warning(
                    "Yellow validateSession returned error for session=%s: %s",
                    session_key,
                    response["error"],
                )
                return {
                    "valid": False,
                    "error": response["error"],
                    "message": "Session validation failed on Yellow Network",
                }
            result = response.get("result", {})
            logger.info("Yellow session validated: session=%s wallet=%s", session_key, wallet)
            return {
                "valid": True,
                "session_key": session_key,
                "wallet": wallet,
                "expires_at": result.get("expiresAt"),
                "allowance_remaining": result.get("allowanceRemaining"),
                "app_id": self.app_id,
                "protocol": self.protocol,
                "message": "Session validation successful",
            }
        except Exception as exc:
            logger.error("Yellow validateSession failed: %s", exc)
            return {
                "valid": False,
                "error": "yellow_network_unavailable",
                "mode": "error",
                "message": f"Failed to validate session on Yellow Network: {exc}",
            }

    async def submit_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            ws_client = await self._get_ws_client()

            intent = order_data.get("intent", {})
            receipt = order_data.get("receipt", {})
            session_key = intent.get("session_key", "")

            yellow_order = {
                "side": intent.get("side", "BUY"),
                "asset": intent.get("asset", "ytest.usd"),
                "amount": str(intent.get("amount", 0)),
                "price": str(intent.get("price", 1.0)),
                "wallet": intent.get("user_wallet") or intent.get("wallet"),
                "sessionKey": session_key,
                "receipt": receipt,
                "timestamp": int(asyncio.get_running_loop().time() * 1000),
            }

            logger.info(
                "Submitting order to Yellow Network: side=%s asset=%s amount=%s",
                yellow_order["side"],
                yellow_order["asset"],
                yellow_order["amount"],
            )

            response = await ws_client.send_rpc(
                method="app.submitOrder",
                params=yellow_order,
            )

            if response.get("error"):
                logger.error("Yellow submitOrder error: %s", response["error"])
                return {
                    "error": response["error"],
                    "status": "FAILED",
                    "mode": "error",
                    "message": "Failed to submit order to Yellow Network",
                }

            result = response.get("result", {})
            order_id = result.get("orderId")
            if not order_id:
                logger.error("Yellow submitOrder returned no orderId: %s", result)
                return {
                    "error": "missing_order_id",
                    "status": "FAILED",
                    "mode": "error",
                    "message": "Yellow Network did not return an order ID",
                }

            logger.info("Order submitted to Yellow Network: order_id=%s", order_id)
            return {
                "order_id": order_id,
                "status": result.get("status", "SUBMITTED"),
                "app_id": self.app_id,
                "protocol": self.protocol,
                "intent": intent,
                "receipt": receipt,
                "channel_status": result.get("channelStatus", "ACTIVE"),
                "message": "Order submitted to Yellow Network",
                "yellow_response": result,
            }
        except Exception as exc:
            logger.error("Yellow submitOrder failed: %s", exc)
            return {
                "error": "yellow_network_unavailable",
                "status": "FAILED",
                "mode": "error",
                "message": f"Failed to submit order to Yellow Network: {exc}",
            }

    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        try:
            ws_client = await self._get_ws_client()
            response = await ws_client.get_order_status(order_id)

            if response.get("error"):
                logger.warning(
                    "Yellow getOrderStatus error for order_id=%s: %s",
                    order_id,
                    response["error"],
                )
                return {
                    "error": response["error"],
                    "status": "UNKNOWN",
                    "mode": "error",
                    "message": "Failed to fetch order status from Yellow Network",
                }

            result = response.get("result", {})
            logger.info(
                "Order status fetched: order_id=%s status=%s",
                order_id,
                result.get("status"),
            )
            return {
                "order_id": order_id,
                "status": result.get("status", "UNKNOWN"),
                "channel_state": result.get("channelState"),
                "settlement_status": result.get("settlementStatus"),
                "app_id": self.app_id,
                "details": result.get("details", {}),
                "yellow_response": result,
            }
        except Exception as exc:
            logger.error("Yellow getOrderStatus failed for order_id=%s: %s", order_id, exc)
            return {
                "error": "yellow_network_unavailable",
                "status": "UNKNOWN",
                "mode": "error",
                "message": f"Failed to fetch order status from Yellow Network: {exc}",
            }

    async def get_market_data(self, asset_pair: Optional[str] = None) -> Dict[str, Any]:
        try:
            ws_client = await self._get_ws_client()
            response = await ws_client.send_rpc(
                method="app.getMarketData",
                params={"pair": asset_pair or "ytest.usd"},
            )
            if response.get("error"):
                logger.warning("Yellow getMarketData not supported: %s", response["error"])
                return {
                    "status": "not_supported",
                    "message": "Market data is not available from Yellow Network",
                }
            result = response.get("result", {})
            logger.info("Market data fetched from Yellow Network for pair=%s", asset_pair)
            return result
        except Exception as exc:
            logger.warning("Yellow getMarketData unavailable: %s", exc)
            return {
                "status": "not_supported",
                "message": "Market data is not available from Yellow Network",
            }

    async def health_check(self) -> Dict[str, Any]:
        try:
            ws_client = await self._get_ws_client()
            is_connected = ws_client.is_connected

            ping_success = False
            if is_connected:
                try:
                    response = await ws_client.send_rpc(method="app.ping", params={})
                    ping_success = not bool(response.get("error"))
                except Exception as ping_exc:
                    logger.warning("Yellow ping failed: %s", ping_exc)
                    ping_success = False

            logger.info(
                "Yellow health check: connected=%s ping=%s", is_connected, ping_success
            )
            return {
                "status": "connected" if is_connected else "disconnected",
                "app_id": self.app_id,
                "api_key_configured": bool(self.api_key),
                "websocket_endpoint": self.ws_url,
                "websocket_connected": is_connected,
                "ping_successful": ping_success,
                "protocol": self.protocol,
                "mode": "real-time",
                "integration_status": "ready" if is_connected else "disconnected",
                "message": (
                    "Yellow Network WebSocket connection active"
                    if is_connected
                    else "Yellow Network WebSocket disconnected"
                ),
            }
        except Exception as exc:
            logger.error("Yellow health check error: %s", exc)
            return {
                "status": "error",
                "app_id": self.app_id,
                "api_key_configured": bool(self.api_key),
                "websocket_endpoint": self.ws_url,
                "websocket_connected": False,
                "protocol": self.protocol,
                "mode": "error",
                "integration_status": "error",
                "error": str(exc),
                "message": f"Yellow Network connection error: {exc}",
            }


yellow_client = YellowClient()
