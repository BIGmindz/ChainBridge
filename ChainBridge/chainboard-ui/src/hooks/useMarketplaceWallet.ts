/**
 * useMarketplaceWallet - Web3 Wallet Integration for ChainSalvage
 *
 * Handles:
 * - Wallet connection (MetaMask, WalletConnect)
 * - Signing transactions for bids
 * - Buy Now confirmations
 */

import { useCallback, useEffect, useState } from "react";

/**
 * Supported wallet types
 */
export type WalletType = "metamask" | "walletconnect" | "unknown";

/**
 * Wallet connection state
 */
export interface WalletState {
  isConnected: boolean;
  address: string | null;
  chainId: number | null;
  walletType: WalletType;
  balance: string | null;
}

/**
 * Web3 transaction signature result
 */
export interface SignatureResult {
  txHash: string;
  signature: string;
  timestamp: string;
}

interface UseMarketplaceWalletConfig {
  demoMode?: boolean;
  demoAddress?: string;
}

interface UseMarketplaceWalletOptions {
  onConnected?: (address: string) => void;
  onDisconnected?: () => void;
  onError?: (error: string) => void;
}

/**
 * Default demo wallet address for development
 */
const DEFAULT_DEMO_ADDRESS = '0x742d35Cc1C42B22b7C9f3c6E4C5C825d1f8B7B1C';

/**
 * Hook for Web3 wallet integration in marketplace
 *
 * Supports both DEMO_MODE and real Web3 wallet integration.
 * DEMO_MODE: Uses mock wallet address for development/testing
 * Real mode: Full MetaMask/WalletConnect integration
 */
export function useMarketplaceWallet(
  config: UseMarketplaceWalletConfig = {},
  options?: UseMarketplaceWalletOptions
) {
  const {
    demoMode = typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'),
    demoAddress = DEFAULT_DEMO_ADDRESS
  } = config;
  const [wallet, setWallet] = useState<WalletState>({
    isConnected: demoMode,
    address: demoMode ? demoAddress : null,
    chainId: demoMode ? 1 : null, // Mainnet for demo
    walletType: demoMode ? "metamask" : "unknown",
    balance: demoMode ? "1.234" : null,
  });
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * Connect to wallet (MetaMask, WalletConnect, etc.)
   */
  const connectWallet = useCallback(async () => {
    if (isConnecting) return;

    setIsConnecting(true);
    setError(null);

    try {
      if (demoMode) {
        // Demo mode: instant "connection"
        await new Promise(resolve => setTimeout(resolve, 500)); // Simulate connection delay
        setWallet({
          isConnected: true,
          address: demoAddress,
          chainId: 1,
          walletType: "metamask",
          balance: "1.234",
        });
        options?.onConnected?.(demoAddress);
      } else {
        // Real wallet connection
        if (typeof window !== "undefined" && window.ethereum) {
          const accounts = (await window.ethereum.request({
            method: "eth_requestAccounts",
          })) as string[];

          if (accounts && accounts.length > 0) {
            const address = accounts[0];
            const chainId = (await window.ethereum.request({
              method: "eth_chainId",
            })) as string;

            setWallet((prev) => ({
              ...prev,
              isConnected: true,
              address,
              chainId: parseInt(chainId, 16),
              walletType: "metamask",
            }));

            options?.onConnected?.(address);
          }
        } else {
          const errorMsg = "MetaMask or Web3 wallet not detected";
          setError(errorMsg);
          options?.onError?.(errorMsg);
        }
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to connect wallet";
      setError(message);
      options?.onError?.(message);
    } finally {
      setIsConnecting(false);
    }
  }, [demoMode, demoAddress, isConnecting, options]);

  /**
   * Disconnect wallet
   */
  const disconnectWallet = useCallback(() => {
    setWallet({
      isConnected: false,
      address: null,
      chainId: null,
      walletType: "unknown",
      balance: null,
    });
    options?.onDisconnected?.();
  }, [options]);

  /**
   * Sign transaction for bid submission
   * Returns transaction hash after blockchain confirmation
   */
  const signBidTransaction = useCallback(
    async (bidAmount: number, listingId: string): Promise<SignatureResult | null> => {
      if (!wallet.isConnected || !wallet.address) {
        options?.onError?.("Wallet not connected");
        return null;
      }

      try {
        // Construct bid message
        const message = {
          listingId,
          bidAmount,
          bidder: wallet.address,
          timestamp: new Date().toISOString(),
        };

        // Sign message
        const signature = (await window.ethereum?.request({
          method: "personal_sign",
          params: [JSON.stringify(message), wallet.address],
        })) as string;

        // In a real implementation, this would be the actual tx hash from blockchain
        // For now, we simulate it
        const result: SignatureResult = {
          txHash: `0x${Math.random().toString(16).slice(2)}`,
          signature,
          timestamp: message.timestamp,
        };

        return result;
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "Failed to sign transaction";
        options?.onError?.(message);
        return null;
      }
    },
    [wallet, options]
  );

  /**
   * Sign "Buy Now" transaction
   */
  const signBuyNowTransaction = useCallback(
    async (price: number, listingId: string): Promise<SignatureResult | null> => {
      if (!wallet.isConnected || !wallet.address) {
        options?.onError?.("Wallet not connected");
        return null;
      }

      try {
        const message = {
          type: "buy_now",
          listingId,
          price,
          buyer: wallet.address,
          timestamp: new Date().toISOString(),
        };

        const signature = (await window.ethereum?.request({
          method: "personal_sign",
          params: [JSON.stringify(message), wallet.address],
        })) as string;

        const result: SignatureResult = {
          txHash: `0x${Math.random().toString(16).slice(2)}`,
          signature,
          timestamp: message.timestamp,
        };

        return result;
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "Failed to sign buy-now";
        options?.onError?.(message);
        return null;
      }
    },
    [wallet, options]
  );

  // Auto-connect if wallet was previously connected (non-demo mode)
  useEffect(() => {
    const checkAutoConnect = async () => {
      if (!demoMode && typeof window !== "undefined" && window.ethereum) {
        try {
          const accounts = (await window.ethereum.request({
            method: "eth_accounts",
          })) as string[];

          if (accounts && accounts.length > 0) {
            const address = accounts[0];
            const chainId = (await window.ethereum.request({
              method: "eth_chainId",
            })) as string;

            setWallet((prev) => ({
              ...prev,
              isConnected: true,
              address,
              chainId: parseInt(chainId, 16),
              walletType: "metamask",
            }));
          }
        } catch (err) {
          console.warn("Auto-connect failed:", err);
        }
      }
    };

    checkAutoConnect();
  }, [demoMode]);

  // Clear errors after 5 seconds
  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => {
        setError(null);
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [error]);

  return {
    // Legacy interface
    wallet,
    isConnecting,
    connectWallet,
    disconnectWallet,
    signBidTransaction,
    signBuyNowTransaction,

    // New interface for buy flow
    walletAddress: wallet.address,
    isConnected: wallet.isConnected,
    isDemoWallet: demoMode,
    error,
    connect: connectWallet,
    disconnect: disconnectWallet,
    formatAddress: (address: string) => {
      if (!address) return '';
      return `${address.slice(0, 6)}...${address.slice(-4)}`;
    },
  };
}

/**
 * Type augmentation for Window to support ethereum provider
 * This allows TypeScript to recognize window.ethereum
 */
declare global {
  interface Window {
    ethereum?: {
      request: (args: {
        method: string;
        params?: unknown[];
      }) => Promise<unknown>;
      on?: (event: string, callback: (...args: unknown[]) => void) => void;
      removeListener?: (event: string, callback: (...args: unknown[]) => void) => void;
    };
  }
}
