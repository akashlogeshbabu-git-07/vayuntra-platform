import type { Threat } from '@/types';
import { AlertTriangle } from 'lucide-react';
export function AnomalyFeed({ threats }: { threats?: Threat[] }) {
  return (
    <div className="space-y-2 max-h-64 overflow-y-auto">
      {(threats || []).slice(0, 8).map((t) => (
        <div key={t.id} className="flex items-center gap-3 p-2.5 rounded-lg bg-gray-900 border border-gray-800">
          <AlertTriangle size={14} className="text-red-400 shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-xs text-white truncate">{t.title}</p>
            <p className="text-xs text-gray-500">Score: {(t.anomaly_score * 100).toFixed(0)}%</p>
          </div>
        </div>
      ))}
    </div>
  );
}
