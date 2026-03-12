import type { Threat } from '@/types';
import { ThreatSeverityBadge } from './ThreatSeverityBadge';
import { formatDistanceToNow } from 'date-fns';

export function ThreatTimeline({ threats }: { threats: Threat[] }) {
  if (!threats?.length) return <p className="text-gray-500 text-sm">No recent threats.</p>;
  return (
    <div className="space-y-2">
      {threats.map((t) => (
        <div key={t.id} className="flex items-start gap-3 p-3 rounded-lg bg-gray-900 hover:bg-gray-800 transition-colors cursor-pointer">
          <ThreatSeverityBadge severity={t.severity} />
          <div className="flex-1 min-w-0">
            <p className="text-sm text-white font-medium truncate">{t.title}</p>
            <p className="text-xs text-gray-500">{t.mitre_tactic} • {formatDistanceToNow(new Date(t.created_at), { addSuffix: true })}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
