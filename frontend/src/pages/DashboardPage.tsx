import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Shield, AlertTriangle, Activity, Server, TrendingUp, Zap } from 'lucide-react';
import { MetricCard } from '@/components/shared/MetricCard';
import { ThreatTimeline } from '@/components/threats/ThreatTimeline';
import { AnomalyFeed } from '@/components/alerts/AnomalyFeed';
import { AgentStatusGrid } from '@/components/dashboard/AgentStatusGrid';
import { MITREHeatmap } from '@/components/dashboard/MITREHeatmap';
import { ThreatTrendChart } from '@/components/dashboard/ThreatTrendChart';
import { QuickActionsPanel } from '@/components/dashboard/QuickActionsPanel';
import { fetchDashboardStats, fetchRecentThreats, fetchAgents } from '@/utils/api';

const REFRESH = 15_000;

export function DashboardPage() {
  const [timeWindow, setTimeWindow] = useState<24 | 48 | 168>(24);

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['dashboard-stats', timeWindow],
    queryFn: () => fetchDashboardStats(timeWindow),
    refetchInterval: REFRESH,
  });

  const { data: threatsData } = useQuery({
    queryKey: ['recent-threats'],
    queryFn: () => fetchRecentThreats({ page_size: 8 }),
    refetchInterval: REFRESH,
  });

  const { data: agentsData } = useQuery({
    queryKey: ['agents'],
    queryFn: () => fetchAgents({ page_size: 6 }),
    refetchInterval: REFRESH,
  });

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <Shield className="text-cyan-400" size={26} />
            Security Operations Center
          </h1>
          <p className="text-gray-400 text-sm mt-0.5">Vayuntra — Real-time Threat Intelligence</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex gap-1 bg-gray-800 rounded-lg p-1">
            {([24, 48, 168] as const).map(w => (
              <button key={w} onClick={() => setTimeWindow(w)}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${timeWindow === w ? 'bg-cyan-600 text-white' : 'text-gray-400 hover:text-white'}`}>
                {w === 168 ? '7d' : `${w}h`}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-1.5 text-green-400 text-xs">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500" />
            </span>
            LIVE
          </div>
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 xl:grid-cols-6 gap-4 mb-6">
        <MetricCard title="Total Threats" value={stats?.total ?? '—'} icon={AlertTriangle} color="red" isLoading={statsLoading} />
        <MetricCard title="Critical" value={stats?.critical ?? '—'} icon={Zap} color="red" isLoading={statsLoading} />
        <MetricCard title="High" value={stats?.high ?? '—'} icon={TrendingUp} color="orange" isLoading={statsLoading} />
        <MetricCard title="Active" value={stats?.active ?? '—'} icon={Activity} color="yellow" isLoading={statsLoading} />
        <MetricCard title="Total Agents" value={stats?.total_agents ?? '—'} icon={Server} color="cyan" isLoading={statsLoading} />
        <MetricCard title="Online" value={stats?.online_agents ?? '—'} icon={Shield} color="green" isLoading={statsLoading} />
      </div>

      {/* Quick Actions */}
      <div className="mb-6">
        <QuickActionsPanel />
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent threats */}
        <div className="lg:col-span-2 bg-gray-900 rounded-xl border border-gray-800 p-5">
          <h2 className="text-sm font-semibold text-gray-300 mb-4">Recent Threats</h2>
          <ThreatTimeline threats={threatsData?.threats || []} />
        </div>

        {/* Right column */}
        <div className="space-y-6">
          {/* Anomaly feed */}
          <div className="bg-gray-900 rounded-xl border border-gray-800 p-5">
            <h2 className="text-sm font-semibold text-gray-300 mb-4">Anomaly Feed</h2>
            <AnomalyFeed threats={threatsData?.threats} />
          </div>
          {/* Agents */}
          <div className="bg-gray-900 rounded-xl border border-gray-800 p-5">
            <h2 className="text-sm font-semibold text-gray-300 mb-4">Agent Status</h2>
            <AgentStatusGrid agents={agentsData?.agents} />
          </div>
        </div>
      </div>

      {/* Bottom row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-5">
          <h2 className="text-sm font-semibold text-gray-300 mb-4">Threat Trend (24h)</h2>
          <ThreatTrendChart trend={stats?.trend} />
        </div>
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-5">
          <h2 className="text-sm font-semibold text-gray-300 mb-4">MITRE ATT&CK Coverage</h2>
          <MITREHeatmap breakdown={stats?.mitre_breakdown} />
        </div>
      </div>
    </div>
  );
}
