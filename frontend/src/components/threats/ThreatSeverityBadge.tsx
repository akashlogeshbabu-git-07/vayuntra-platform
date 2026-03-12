import type { ThreatSeverity, ThreatStatus } from '@/types';

const severityMap: Record<ThreatSeverity, string> = {
  critical: 'bg-red-900/50 text-red-300 border border-red-700',
  high: 'bg-orange-900/50 text-orange-300 border border-orange-700',
  medium: 'bg-yellow-900/50 text-yellow-300 border border-yellow-700',
  low: 'bg-blue-900/50 text-blue-300 border border-blue-700',
  info: 'bg-gray-800 text-gray-400 border border-gray-700',
};

const statusMap: Record<ThreatStatus, string> = {
  detected: 'bg-red-900/40 text-red-300',
  investigating: 'bg-orange-900/40 text-orange-300',
  contained: 'bg-yellow-900/40 text-yellow-300',
  remediated: 'bg-green-900/40 text-green-300',
  false_positive: 'bg-gray-800 text-gray-400',
  closed: 'bg-gray-800 text-gray-400',
};

export function ThreatSeverityBadge({ severity }: { severity: ThreatSeverity }) {
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-semibold uppercase tracking-wide ${severityMap[severity]}`}>
      {severity}
    </span>
  );
}

export function ThreatStatusBadge({ status }: { status: ThreatStatus }) {
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium capitalize ${statusMap[status]}`}>
      {status.replace('_', ' ')}
    </span>
  );
}
