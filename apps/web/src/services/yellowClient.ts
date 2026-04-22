'use client';

import {
  createAppSessionMessage,
  createAuthRequestMessage,
  createAuthVerifyMessageFromChallenge,
  parseAnyRPCResponse,
  RPCProtocolVersion,
  RPCMethod,
  type MessageSigner,
  type RPCData,
  type RPCAppDefinition,
  type RPCAppSessionAllocation,
  type AuthChallengeResponse,
} from '@erc7824/nitrolite';
import type { Hex, Address } from 'viem';

export class YellowNetworkClient {
  private ws: WebSocket | null = null;
  private signer: MessageSigner | null = null;
  private userAddress: string | null = null;
  private sessionId: string | null = null;
  private authChallenge: string | null = null;
  private isAuthenticated = false;
  private messageHandlers: Map<string, (data: unknown) => void> = new Map();
  private pendingResolvers: Map<string, (data: unknown) => void> = new Map();

  constructor(private endpoint: string = 'wss://clearnet-sandbox.yellow.com/ws') {}

  async init() {
    const { userAddress, signer } = await this.setupWallet();
    this.userAddress = userAddress;
    this.signer = signer;
    await this.connect();
  }

  async setupWallet(): Promise<{ userAddress: string; signer: MessageSigner }> {
    if (typeof window === 'undefined' || !(window as any).ethereum) {
      throw new Error('Please install MetaMask');
    }

    const accounts: string[] = await (window as any).ethereum.request({
      method: 'eth_requestAccounts',
    });

    const userAddress = accounts[0];

    const signer: MessageSigner = async (payload: RPCData): Promise<Hex> => {
      const messageStr = JSON.stringify(payload);
      const signature: string = await (window as any).ethereum.request({
        method: 'personal_sign',
        params: [messageStr, userAddress],
      });
      return signature as Hex;
    };

    console.log('✅ Wallet connected:', userAddress);
    return { userAddress, signer };
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(this.endpoint);

      this.ws.onopen = async () => {
        console.log('✅ WebSocket connected to Yellow Network!');
        resolve();
      };

      this.ws.onerror = (error) => {
        console.error('Yellow Network WebSocket error:', error);
        reject(new Error('WebSocket connection failed'));
      };

      this.ws.onmessage = (event: MessageEvent) => {
        this.handleMessage(event.data as string);
      };

      this.ws.onclose = () => {
        console.log('Yellow Network connection closed');
        this.isAuthenticated = false;
      };
    });
  }

  private handleMessage(rawData: string) {
    try {
      parseAnyRPCResponse(rawData);
      const msg = JSON.parse(rawData);

      const method: string =
        msg?.res?.[1] ?? msg?.method ?? msg?.type ?? 'unknown';

      const resolver = this.pendingResolvers.get(method);
      if (resolver) {
        resolver(msg);
        this.pendingResolvers.delete(method);
      }

      const handler = this.messageHandlers.get(method);
      if (handler) handler(msg);

      if (method === RPCMethod.AuthChallenge) {
        this.authChallenge =
          msg?.res?.[2]?.challenge ?? msg?.params?.challenge_message ?? null;
        console.log('🔑 Auth challenge received');
      }

      if (method === RPCMethod.AuthVerify) {
        this.isAuthenticated = true;
        console.log('✅ Authenticated with Yellow Network!');
      }

      if (method === RPCMethod.CreateAppSession) {
        this.sessionId = msg?.res?.[2]?.app_session_id ?? null;
        console.log('✅ App session created:', this.sessionId);
      }
    } catch (err) {
      console.error('Error handling Yellow message:', err);
    }
  }

  private waitFor(method: string, timeoutMs = 15000): Promise<unknown> {
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pendingResolvers.delete(method);
        reject(new Error(`Timeout waiting for ${method}`));
      }, timeoutMs);

      this.pendingResolvers.set(method, (data) => {
        clearTimeout(timer);
        resolve(data);
      });
    });
  }

  private send(message: string) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket not connected');
    }
    this.ws.send(message);
  }

  async authenticate(): Promise<void> {
    if (!this.signer || !this.userAddress) {
      throw new Error('Wallet not set up');
    }

    const challengeWaiter = this.waitFor(RPCMethod.AuthChallenge);

    const authRequestMsg = await createAuthRequestMessage({
      address: this.userAddress as Address,
      session_key: this.userAddress as Address,
      application: 'CompliFlow',
      allowances: [{ asset: 'usdc', amount: '1000000' }],
      expires_at: BigInt(Math.floor(Date.now() / 1000) + 86400 * 30),
      scope: 'app',
    });

    this.send(authRequestMsg);
    await challengeWaiter;

    if (!this.authChallenge) throw new Error('No auth challenge received');

    const verifyWaiter = this.waitFor(RPCMethod.AuthVerify);

    const verifyMsg = await createAuthVerifyMessageFromChallenge(
      this.signer,
      this.authChallenge
    );
    this.send(verifyMsg);
    await verifyWaiter;

    console.log('✅ Yellow Network authentication complete!');
  }

  async createSession(
    partnerAddress: string,
    userAllocation = '800000',
    partnerAllocation = '200000'
  ) {
    if (!this.signer || !this.userAddress) throw new Error('Wallet not connected');
    if (!this.isAuthenticated) await this.authenticate();

    const definition: RPCAppDefinition = {
      application: 'CompliFlow',
      protocol: RPCProtocolVersion.NitroRPC_0_4,
      participants: [this.userAddress as Hex, partnerAddress as Hex],
      weights: [50, 50],
      quorum: 100,
      challenge: 0,
      nonce: Date.now(),
    };

    const allocations: RPCAppSessionAllocation[] = [
      { participant: this.userAddress as Address, asset: 'usdc', amount: userAllocation },
      { participant: partnerAddress as Address, asset: 'usdc', amount: partnerAllocation },
    ];

    const sessionWaiter = this.waitFor(RPCMethod.CreateAppSession);

    const sessionMsg = await createAppSessionMessage(this.signer, {
      definition,
      allocations,
    });

    this.send(sessionMsg);
    await sessionWaiter;

    console.log('✅ Session created:', this.sessionId);
    return { definition, allocations, sessionId: this.sessionId };
  }

  async sendPayment(amount: string, recipient: string) {
    if (!this.signer || !this.userAddress) throw new Error('Wallet not connected');

    const payload = JSON.stringify({
      type: 'payment',
      amount,
      recipient,
      sender: this.userAddress,
      timestamp: Date.now(),
    });

    const signature: Hex = await (this.signer as any)(payload);
    const signed = { type: 'payment', amount, recipient, sender: this.userAddress, signature };
    this.send(JSON.stringify(signed));
    console.log('💸 Payment sent:', amount);
    return signed;
  }

  async submitOrder(orderData: {
    side: string;
    asset: string;
    amount: number;
    price: number;
    sessionKey: string;
  }) {
    if (!this.signer || !this.userAddress) throw new Error('Wallet not connected');

    const order = {
      type: 'order',
      side: orderData.side,
      asset: orderData.asset,
      amount: String(orderData.amount),
      price: String(orderData.price),
      wallet: this.userAddress,
      sessionKey: orderData.sessionKey,
      timestamp: Date.now(),
    };

    const payload = JSON.stringify(order);
    const signature: string = await (window as any).ethereum.request({
      method: 'personal_sign',
      params: [payload, this.userAddress],
    });

    const signed = { ...order, signature };
    this.send(JSON.stringify(signed));
    console.log('✅ Order submitted to Yellow Network:', signed);
    return signed;
  }

  on(event: string, handler: (data: unknown) => void) {
    this.messageHandlers.set(event, handler);
  }

  getSessionId() { return this.sessionId; }
  getUserAddress() { return this.userAddress; }
  getIsAuthenticated() { return this.isAuthenticated; }
  isConnected() { return this.ws?.readyState === WebSocket.OPEN; }

  disconnect() {
    this.ws?.close();
    this.ws = null;
    this.sessionId = null;
    this.isAuthenticated = false;
  }
}

export const yellowClient = new YellowNetworkClient();
