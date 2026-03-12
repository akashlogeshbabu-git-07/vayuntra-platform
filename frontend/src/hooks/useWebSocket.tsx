import { createContext, useContext, ReactNode } from 'react';
const WSContext = createContext<any>(null);
export function WebSocketProvider({ children }: { children: ReactNode }) {
  return <WSContext.Provider value={{ connected: false }}>{children}</WSContext.Provider>;
}
export function useWebSocket() { return useContext(WSContext); }
