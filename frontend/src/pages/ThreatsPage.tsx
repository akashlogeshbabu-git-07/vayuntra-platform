import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { AlertTriangle, Search, Shield, Zap } from 'lucide-react';
import { fetchThreats, isolateThreat, remediateThreat } from '@/utils/api';
import { ThreatSeverityBadge, ThreatStatusBadge } from '@/components/threats/ThreatSeverityBadge';
import type { Threat } from '@/types';
import { formatDistanceToNow } from 'date-fns';

export function ThreatsPage() {
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState<Threat | null>(null);
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['threats'],
    queryFn: () => fetchThreats({ page_size: 50 }),
    refetchInterval: 15000,
  });

  const remediateMutation = useMutation({
    mutationFn: (id: string) => remediateThreat(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['threats'] }); setSelected(null); },
  });

  const isolateMutation = useMutation({
    mutationFn: (id: string) => isolateThreat(id, { isolation_type: 'network' }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['threats'] }); setSelected(null); },
  });

  const threats: Threat[] = data?.threats || [];
  const filtered = threats.filter(t =>
    t.title.toLowerCase().includes(search.toLowerCase()) ||
    t.mitre_tactic?.toLowerCase().includes(search.toLowerCase()) ||
    t.source_ip?.includes(search)
  );

  return (
    <div className="p-6 bg-gray-950 min-h-screen">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-white flex items-center gap-3">
          <AlertTriangle className="text-red-400" size={24} />
          Threats ({data?.total ?? 0})
        </h1>
      </div>

      <div className="relative mb-4">
        <Search size={16} className="absolute left-3 top-3 text-gray-500" />
        <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search threats, tactics, IPs..."
          className="w-full pl-9 pr-4 py-2.5 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500 text-sm" />
      </div>

      <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800 text-gray-400 text-xs uppercase tracking-wide">
              <th className="text-left p-4">Severity</th>
              <th className="text-left p-4">Threat</th>
              <th className="text-left p-4 hidden md:table-cell">MITRE Tactic</th>
              <th className="text-left p-4 hidden lg:table-cell">Source IP</th>
              <th className="text-left p-4">Status</th>
              <th className="text-left p-4 hidden md:table-cell">Detected</th>
              <th className="text-right p-4">Actions</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr><td colSpan={7} className="p-8 text-center text-gray-500">Loading...</td></tr>
            )}
            {!isLoading && filtered.length === 0 && (
              <tr><td colSpan={7} className="p-8 text-center text-gray-500">No threats found</td></tr>
            )}
            {filtered.map(t => (
              <tr key={t.id} onClick={() => setSelected(t)}
                className="border-b border-gray-800/50 hover:bg-gray-800/50 transition-colors cursor-pointer">
                <td className="p-4"><ThreatSeverityBadge severity={t.severity} /></td>
                <td className="p-4">
                  <p className="text-white font-medium">{t.title}</p>
                  <p className="text-gray-500 text-xs">{t.process_name}</p>
                </td>
                <td className="p-4 hidden md:table-cell text-gray-400">{t.mitre_tactic || '—'}</td>
                <td className="p-4 hidden lg:table-cell text-gray-400 font-mono text-xs">{t.source_ip || '—'}</td>
                <td className="p-4"><ThreatStatusBadge status={t.status} /></td>
                <td className="p-4 hidden md:table-cell text-gray-500 text-xs">
                  {formatDistanceToNow(new Date(t.created_at), { addSuffix: true })}
                </td>
                <td className="p-4 text-right">
                  <div className="flex justify-end gap-2" onClick={e => e.stopPropagation()}>
                    {t.status === 'detected' || t.status === 'investigating' ? (
                      <>
                        <button onClick={() => isolateMutation.mutate(t.id)}
                          className="px-2 py-1 text-xs bg-yellow-800/60 text-yellow-300 rounded hover:bg-yellow-700/60 transition-colors">
                          Isolate
                        </button>
                        <button onClick={() => remediateMutation.mutate(t.id)}
                          className="px-2 py-1 text-xs bg-cyan-800/60 text-cyan-300 rounded hover:bg-cyan-700/60 transition-colors">
                          Remediate
                        </button>
                      </>
                    ) : null}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Threat Detail Panel */}
      {selected && (
        <div className="fixed inset-0 bg-black/60 z-50 flex justify-end" onClick={() => setSelected(null)}>
          <div className="w-full max-w-lg bg-gray-900 h-full overflow-y-auto p-6" onClick={e => e.stopPropagation()}>
            <div className="flex items-start justify-between mb-4">
              <ThreatSeverityBadge severity={selected.severity} />
              <button onClick={() => setSelected(null)} className="text-gray-500 hover:text-white">✕</button>
            </div>
            <h2 className="text-white font-bold text-lg mb-2">{selected.title}</h2>
            <ThreatStatusBadge status={selected.status} />
            <div className="mt-4 space-y-3 text-sm">
              {[
                ['MITRE Tactic', selected.mitre_tactic], ['Technique', selected.mitre_technique],
                ['Source IP', selected.source_ip], ['Dest IP', selected.dest_ip],
                ['Process', selected.process_name],
                ['Confidence', `${(selected.confidence_score * 100).toFixed(0)}%`],
                ['Anomaly Score', `${(selected.anomaly_score * 100).toFixed(0)}%`],
              ].filter(([, v]) => v).map(([k, v]) => (
                <div key={String(k)} className="flex gap-3">
                  <span className="text-gray-500 w-32 shrink-0">{k}</span>
                  <span className="text-white font-mono text-xs">{v}</span>
                </div>
              ))}
            </div>
            {selected.description && (
              <div className="mt-4 p-3 bg-gray-800 rounded-lg">
                <p className="text-xs text-gray-400">{selected.description}</p>
              </div>
            )}
            {selected.remediation_playbook && (
              <div className="mt-4">
                <p className="text-xs text-gray-400 font-semibold mb-2 uppercase tracking-wide">Remediation Playbook</p>
                <div className="bg-gray-800 rounded-lg p-3">
                  <pre className="text-xs text-green-300 whitespace-pre-wrap">{selected.remediation_playbook}</pre>
                </div>
              </div>
            )}
            {(selected.status === 'detected' || selected.status === 'investigating') && (
              <div className="mt-6 flex gap-3">
                <button onClick={() => isolateMutation.mutate(selected.id)}
                  className="flex-1 py-2 bg-yellow-700/40 text-yellow-300 rounded-lg text-sm font-medium hover:bg-yellow-700/60 transition-colors flex items-center justify-center gap-2">
                  <Shield size={14} /> Isolate
                </button>
                <button onClick={() => remediateMutation.mutate(selected.id)}
                  className="flex-1 py-2 bg-cyan-700/40 text-cyan-300 rounded-lg text-sm font-medium hover:bg-cyan-700/60 transition-colors flex items-center justify-center gap-2">
                  <Zap size={14} /> Remediate
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
