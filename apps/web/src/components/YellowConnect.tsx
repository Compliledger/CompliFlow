'use client';

import { useState, useEffect } from 'react';
import { yellowClient } from '@/services/yellowClient';

export default function YellowConnect() {
  const [isConnected, setIsConnected] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [userAddress, setUserAddress] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    yellowClient.on('create_app_session', (data: unknown) => {
      const msg = data as Record<string, any>;
      const appSessionId = msg?.res?.[2]?.app_session_id ?? null;
      if (appSessionId) {
        setSessionId(appSessionId);
        console.log('Session created:', appSessionId);
      }
    });

    yellowClient.on('auth_verify', () => {
      setIsAuthenticated(true);
    });

    return () => {
      yellowClient.disconnect();
    };
  }, []);

  const connectToYellow = async () => {
    setIsConnecting(true);
    setError(null);

    try {
      await yellowClient.init();
      setUserAddress(yellowClient.getUserAddress());
      setIsConnected(true);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to connect';
      setError(msg);
    } finally {
      setIsConnecting(false);
    }
  };

  const authenticate = async () => {
    setIsAuthenticating(true);
    setError(null);

    try {
      await yellowClient.authenticate();
      setIsAuthenticated(yellowClient.getIsAuthenticated());
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Authentication failed';
      setError(msg);
    } finally {
      setIsAuthenticating(false);
    }
  };

  const createSession = async () => {
    setError(null);
    try {
      const result = await yellowClient.createSession(
        '0x0000000000000000000000000000000000000001'
      );
      if (result?.sessionId) setSessionId(result.sessionId);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Session creation failed';
      setError(msg);
    }
  };

  const disconnect = () => {
    yellowClient.disconnect();
    setIsConnected(false);
    setIsAuthenticated(false);
    setUserAddress(null);
    setSessionId(null);
  };

  return (
    <div className="fixed bottom-4 right-4 z-50">
      <div className="bg-black/90 backdrop-blur-sm border border-yellow-500/30 rounded-lg p-4 shadow-xl min-w-[220px]">
        <div className="flex items-center gap-3 mb-3">
          <div
            className={`w-2 h-2 rounded-full ${
              sessionId
                ? 'bg-green-400'
                : isAuthenticated
                ? 'bg-yellow-400'
                : isConnected
                ? 'bg-blue-400'
                : 'bg-red-500'
            }`}
          />
          <span className="text-yellow-400 font-semibold text-sm">Yellow Network</span>
        </div>

        {!isConnected && (
          <button
            onClick={connectToYellow}
            disabled={isConnecting}
            className="w-full px-4 py-2 bg-gradient-to-r from-yellow-500 to-yellow-600 text-black font-medium rounded-md hover:from-yellow-400 hover:to-yellow-500 transition-all disabled:opacity-50 text-sm"
          >
            {isConnecting ? 'Connecting...' : 'Connect Wallet'}
          </button>
        )}

        {isConnected && !isAuthenticated && (
          <div className="space-y-2">
            <div className="text-xs text-gray-400 font-mono">
              {userAddress?.slice(0, 6)}...{userAddress?.slice(-4)}
            </div>
            <button
              onClick={authenticate}
              disabled={isAuthenticating}
              className="w-full px-3 py-1.5 bg-yellow-500/20 text-yellow-400 text-xs rounded hover:bg-yellow-500/30 transition-all disabled:opacity-50"
            >
              {isAuthenticating ? 'Authenticating...' : 'Authenticate'}
            </button>
            <button
              onClick={disconnect}
              className="w-full px-3 py-1.5 bg-red-500/20 text-red-400 text-xs rounded hover:bg-red-500/30 transition-all"
            >
              Disconnect
            </button>
          </div>
        )}

        {isConnected && isAuthenticated && (
          <div className="space-y-2">
            <div className="text-xs text-gray-400">
              <div className="font-mono mb-1">
                {userAddress?.slice(0, 6)}...{userAddress?.slice(-4)}
              </div>
              <div className="text-green-400">✅ Authenticated</div>
              {sessionId && (
                <div className="text-yellow-400 mt-1">
                  Session: {sessionId.slice(0, 10)}...
                </div>
              )}
            </div>

            {!sessionId && (
              <button
                onClick={createSession}
                className="w-full px-3 py-1.5 bg-yellow-500/20 text-yellow-400 text-xs rounded hover:bg-yellow-500/30 transition-all"
              >
                Create Session
              </button>
            )}

            <button
              onClick={disconnect}
              className="w-full px-3 py-1.5 bg-red-500/20 text-red-400 text-xs rounded hover:bg-red-500/30 transition-all"
            >
              Disconnect
            </button>
          </div>
        )}

        {error && (
          <div className="mt-2 text-xs text-red-400 bg-red-500/10 p-2 rounded break-words">
            {error}
          </div>
        )}
      </div>
    </div>
  );
}
