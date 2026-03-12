import { createContext, useContext, ReactNode } from 'react';
const NotifContext = createContext<any>(null);
export function NotificationProvider({ children }: { children: ReactNode }) {
  return <NotifContext.Provider value={{ notifications: [] }}>{children}</NotifContext.Provider>;
}
export function useNotifications() { return useContext(NotifContext); }
