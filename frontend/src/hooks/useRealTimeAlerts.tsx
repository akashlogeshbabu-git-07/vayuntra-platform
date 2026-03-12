import { useState } from 'react';
export function useRealTimeAlerts() {
  const [liveAlerts] = useState<any[]>([]);
  const [alertCount] = useState(0);
  return { liveAlerts, alertCount };
}
