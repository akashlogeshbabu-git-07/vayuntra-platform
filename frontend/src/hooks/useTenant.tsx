import { createContext, useContext, ReactNode } from 'react';
import { useAuth } from './useAuth';
const TenantContext = createContext<any>(null);
export function TenantProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  return <TenantContext.Provider value={{ tenantId: user?.tenant_id }}>{children}</TenantContext.Provider>;
}
export function useTenant() { return useContext(TenantContext); }
