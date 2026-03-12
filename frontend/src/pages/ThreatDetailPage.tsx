import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { fetchThreat } from '@/utils/api';
import { ArrowLeft } from 'lucide-react';
import { ThreatSeverityBadge, ThreatStatusBadge } from '@/components/threats/ThreatSeverityBadge';

export function ThreatDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: threat, isLoading } = useQuery({ queryKey: ['threat', id], queryFn: () => fetchThreat(id!), enabled: !!id });
  if (isLoading) return <div className="p-6 text-gray-400">Loading...</div>;
  if (!threat) return <div className="p-6 text-gray-400">Threat not found</div>;
  return (
    <div className="p-6 bg-gray-950 min-h-screen">
      <button onClick={() => navigate(-1)} className="flex items-center gap-2 text-gray-400 hover:text-white mb-6 text-sm">
        <ArrowLeft size={16} /> Back to threats
      </button>
      <div className="flex gap-3 mb-4"><ThreatSeverityBadge severity={threat.severity} /><ThreatStatusBadge status={threat.status} /></div>
      <h1 className="text-2xl font-bold text-white mb-6">{threat.title}</h1>
      {threat.remediation_playbook && (
        <div className="bg-gray-900 rounded-xl border border-gray-800 p-5">
          <h2 className="text-sm font-semibold text-gray-300 mb-3">Remediation Playbook</h2>
          <pre className="text-sm text-green-300 whitespace-pre-wrap">{threat.remediation_playbook}</pre>
        </div>
      )}
    </div>
  );
}
