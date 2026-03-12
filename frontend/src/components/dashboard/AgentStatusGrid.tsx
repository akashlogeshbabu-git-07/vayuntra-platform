import type { Agent } from '@/types';
const statusColor: Record<string, string> = {
  online: 'bg-green-500', offline: 'bg-gray-600', isolated: 'bg-yellow-500', updating: 'bg-blue-500', error: 'bg-red-500',
};
export function AgentStatusGrid({ agents }: { agents?: Agent[] }) {
  if (!agents?.length) return <p className="text-gray-500 text-sm">No agents registered.</p>;
  return (
    <div className="grid grid-cols-2 gap-2">
      {agents.slice(0, 6).map((a) => (
        <div key={a.id} className="flex items-center gap-2 p-3 rounded-lg bg-gray-900 border border-gray-800">
          <span className={`w-2 h-2 rounded-full shrink-0 ${statusColor[a.status] || 'bg-gray-500'}`} />
          <div className="min-w-0">
            <p className="text-xs text-white font-medium truncate">{a.hostname}</p>
            <p className="text-xs text-gray-500">{a.ip_address}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
