import { useQuery } from '@tanstack/react-query';
import { Server, Wifi, WifiOff } from 'lucide-react';
import { fetchAgents } from '@/utils/api';
import type { Agent } from '@/types';
import { formatDistanceToNow } from 'date-fns';

const statusColor: Record<string, string> = {
  online: 'text-green-400 bg-green-900/30', offline: 'text-gray-400 bg-gray-800',
  isolated: 'text-yellow-400 bg-yellow-900/30', updating: 'text-blue-400 bg-blue-900/30', error: 'text-red-400 bg-red-900/30',
};

export function AgentsPage() {
  const { data, isLoading } = useQuery({ queryKey: ['agents-full'], queryFn: () => fetchAgents({ page_size: 100 }), refetchInterval: 15000 });
  const agents: Agent[] = data?.agents || [];

  return (
    <div className="p-6 bg-gray-950 min-h-screen">
      <h1 className="text-2xl font-bold text-white flex items-center gap-3 mb-6">
        <Server className="text-cyan-400" size={24} /> Agents ({data?.total ?? 0})
      </h1>
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {isLoading && <p className="text-gray-500">Loading agents...</p>}
        {agents.map(a => (
          <div key={a.id} className="bg-gray-900 border border-gray-800 rounded-xl p-5 hover:border-gray-700 transition-colors">
            <div className="flex items-start justify-between mb-3">
              <div>
                <p className="text-white font-semibold">{a.hostname}</p>
                <p className="text-gray-500 text-xs font-mono">{a.ip_address}</p>
              </div>
              <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusColor[a.status] || 'text-gray-400 bg-gray-800'}`}>
                {a.status}
              </span>
            </div>
            <div className="space-y-1.5 text-xs text-gray-400">
              <div className="flex justify-between"><span>OS</span><span className="text-white capitalize">{a.os} {a.os_version ? `· ${a.os_version}` : ''}</span></div>
              <div className="flex justify-between"><span>Agent Version</span><span className="text-white">{a.agent_version}</span></div>
              {a.last_seen && <div className="flex justify-between"><span>Last Seen</span><span className="text-white">{formatDistanceToNow(new Date(a.last_seen), { addSuffix: true })}</span></div>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
