# CompliFlow Testing Guide

## ⚠️ **CURRENT STATUS**

### **Yellow Network Connection: FALLBACK MODE**

```
✅ Backend deployed: Railway
✅ Frontend deployed: Vercel
❌ Yellow Network: NOT CONNECTED
❌ Testnet: NOT ACTIVE
❌ On-chain: NOT YET
```

---

## 🔍 **Connection Status**

**Endpoint:** `wss://clearnet-sandbox.yellow.com/ws`
**Status:** `disconnected`
**Mode:** `FALLBACK`

**Why it's not connecting:**
1. Yellow Network sandbox may require allowlisting
2. WebSocket authentication may need specific handshake
3. Yellow sandbox endpoint might be restricted to approved apps
4. May need to register app on Yellow Network dashboard first

**Current Behavior:**
- Backend gracefully falls back to simulation mode
- All APIs work with mock responses
- Full flow can be demonstrated
- Audit logging and compliance features fully functional

---

## 🧪 **HOW TO TEST (Current Fallback Mode)**

### **Test 1: Health Check**
```bash
curl -X GET "https://compli-flow-backend-production.up.railway.app/v1/yellow/health"
```

**Expected Response:**
```json
{
  "status": "disconnected",
  "websocket_connected": false,
  "mode": "real-time",
  "integration_status": "disconnected",
  "message": "Yellow Network WebSocket disconnected"
}
```

---

### **Test 2: Complete Order Flow**

#### **Step 1: Evaluate Intent**
```bash
curl -X POST "https://compli-flow-backend-production.up.railway.app/v1/intent/evaluate" \
  -H "Content-Type: application/json" \
  -d '{
    "session_key": "demo-session-001",
    "user_wallet": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
    "side": "BUY",
    "asset": "ytest.usd",
    "amount": 100,
    "price": 1.0,
    "expires_at": 1800000000,
    "jurisdiction": "US"
  }'
```

**Response:**
```json
{
  "payload": {
    "intent": {...},
    "decision": {"status": "PASS"}
  },
  "signature": "whbM2jN5gu8...",
  "receipt_hash": "d95fc1ceadaf1b4af3079a4186075e95b41562954d12c240341b044ae0b2ab8b",
  "order_id": "order_45bd4dd1b941"
}
```

✅ **Session governance working**
✅ **Policy evaluation working**
✅ **Audit logging active**
✅ **Receipt signing working**

---

#### **Step 2: Submit Order to Yellow**
```bash
curl -X POST "https://compli-flow-backend-production.up.railway.app/v1/yellow/order/submit" \
  -H "Content-Type: application/json" \
  -d '{
    "intent": {
      "session_key": "demo-session-001",
      "user_wallet": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
      "side": "BUY",
      "asset": "ytest.usd",
      "amount": 100,
      "price": 1.0
    },
    "receipt": {
      "payload": {
        "intent": {...},
        "decision": {"status": "PASS"}
      },
      "signature": "your_signature_here"
    }
  }'
```

**Response (Fallback Mode):**
```json
{
  "order_id": "yellow_order_f00e42d0041b",
  "status": "SUBMITTED",
  "channel_status": "FALLBACK",
  "message": "Order submitted (fallback mode): Not connected to Yellow Network"
}
```

---

#### **Step 3: Check Order Status**
```bash
curl -X GET "https://compli-flow-backend-production.up.railway.app/v1/yellow/order/yellow_order_f00e42d0041b/status"
```

**Response:**
```json
{
  "order_id": "yellow_order_f00e42d0041b",
  "status": "MATCHED",
  "channel_state": "UPDATED",
  "settlement_status": "PENDING_ONCHAIN",
  "mode": "fallback"
}
```

---

### **Test 3: Session Validation**
```bash
curl -X POST "https://compli-flow-backend-production.up.railway.app/v1/yellow/session/preflight" \
  -H "Content-Type: application/json" \
  -d '{
    "session_key": "demo-session-001",
    "wallet": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
  }'
```

**Response:**
```json
{
  "valid": true,
  "expires_at": 1800000000,
  "allowance_remaining": 10000,
  "session_key": "demo-session-001",
  "wallet": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
}
```

✅ **Session governance working**

---

### **Test 4: Audit Trail**
```bash
curl -X GET "https://compli-flow-backend-production.up.railway.app/v1/audit/logs"
```

✅ **Audit logging functional**

---

## 📊 **ON-CHAIN STATUS**

### **Current State: OFF-CHAIN ONLY**

```
┌─────────────────────────────────────────────┐
│  CompliFlow Backend (Railway)                │
│  ├─ Session Governance ✅                    │
│  ├─ Policy Engine ✅                         │
│  ├─ Audit Logging ✅                         │
│  └─ Order State Machine ✅                   │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  Yellow Network (ATTEMPTED)                  │
│  WebSocket: wss://clearnet-sandbox...        │
│  Status: ❌ NOT CONNECTED                    │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  Blockchain Settlement                       │
│  Status: ❌ NOT ACTIVE                       │
└─────────────────────────────────────────────┘
```

**What's Working:**
- ✅ CompliFlow backend (all compliance features)
- ✅ Session governance (expiration, allowance, wallet binding)
- ✅ Policy evaluation
- ✅ Cryptographic receipts
- ✅ Audit trail
- ✅ Order state machine

**What's NOT Working:**
- ❌ Real Yellow Network connection
- ❌ State channels
- ❌ On-chain settlement
- ❌ Real-time WebSocket updates

---

## 🚀 **TO ACTIVATE YELLOW NETWORK**

### **Option 1: Register App on Yellow Network**
1. Visit Yellow Network developer portal
2. Register application with APP-4720-5FF0
3. Get proper credentials/allowlisting
4. Configure authentication handshake

### **Option 2: Contact Yellow Team**
During Checkpoint #2 session (8.03.2026):
1. Show current implementation
2. Ask about sandbox access requirements
3. Get testnet credentials
4. Request authentication documentation

### **Option 3: Switch to Production Endpoint**
If sandbox is restricted, may need to go directly to testnet/mainnet:
```python
# Change in yellow_client.py
self.ws_url = "wss://clearnet-testnet.yellow.com/ws"  # If available
```

---

## 🎯 **WHAT CAN BE DEMONSTRATED NOW**

### **For Hackathon Judges:**

**1. Compliance Architecture** ✅
- Session governance with expiration and allowance limits
- Policy engine evaluation before execution
- Cryptographic receipt signing (SHA-256 hashing)
- Complete audit trail for institutional compliance

**2. Order Lifecycle Management** ✅
- State machine with enforced transitions
- Automatic timestamp tracking
- Status progression simulation

**3. API Integration Readiness** ✅
- WebSocket client implemented (Yellow SDK patterns)
- Fallback mode with graceful degradation
- Complete API documentation
- Production-ready error handling

**4. Full Stack Application** ✅
- Frontend: Next.js with Yellow Network branding
- Backend: FastAPI with compliance features
- Deployed: Railway + Vercel

---

## 📋 **TESTING CHECKLIST**

### **Backend Features (All Working):**
- ✅ Session validation
- ✅ Policy evaluation
- ✅ Receipt signing
- ✅ Order submission (fallback)
- ✅ Order status tracking (fallback)
- ✅ Audit logging
- ✅ Health checks
- ✅ Session governance enforcement

### **Yellow Network (Pending):**
- ⏳ WebSocket connection
- ⏳ Real-time state channels
- ⏳ On-chain settlement
- ⏳ Testnet integration

---

## 💡 **RECOMMENDED NEXT STEPS**

1. **For Demo:** Use current fallback mode to show compliance features
2. **For Yellow Team:** Present implementation and request connection guidance
3. **For Production:** Get testnet access and credentials
4. **For On-chain:** Deploy smart contracts after Yellow connection is active

---

## 🎓 **SUMMARY**

**Testnet Status:** ❌ **NOT CONNECTED**
**Sandbox Status:** ❌ **NOT CONNECTED**
**On-chain Status:** ❌ **NOT YET**
**Fallback Mode:** ✅ **FULLY FUNCTIONAL**

**Can Test:**
- ✅ All CompliFlow compliance features
- ✅ Complete order flow (simulated Yellow responses)
- ✅ Session governance
- ✅ Audit trail
- ✅ API endpoints

**Cannot Test:**
- ❌ Real Yellow Network state channels
- ❌ On-chain settlement
- ❌ Real-time WebSocket events
- ❌ Actual blockchain transactions

**Ready for:** Hackathon demo with full compliance architecture showcase
**Waiting for:** Yellow Network sandbox/testnet access
