import { useQuery } from '@tanstack/react-query';
import { fetchThreats, remediateThreat } from '@/utils/api';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Zap } from 'lucide-react';
export function RemediationPage() {
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ['remediation-threats'], queryFn: () => fetchThreats({ page_size: 50 }) });
  const mutation = useMutation({ mutationFn: remediateThreat, onSuccess: () => qc.invalidateQueries({ queryKey: ['remediation-threats'] }) });
  const active = (data?.threats || []).filter((t: any) => ['detected', 'investigating', 'contained'].includes(t.status));
  return (
    <div className="p-6 bg-gray-950 min-h-screen">
      <h1 className="text-2xl font-bold text-white flex items-center gap-3 mb-6"><Zap className="text-cyan-400" size={24} />AI Remediation</h1>
      <div className="space-y-3">
        {active.map((t: any) => (
          <div key={t.id} className="flex items-center justify-between bg-gray-900 rounded-xl border border-gray-800 p-4">
            <div><p className="text-white font-medium">{t.title}</p><p className="text-gray-500 text-sm">{t.mitre_tactic} · {t.severity}</p></div>
            <button onClick={() => mutation.mutate(t.id)} className="px-4 py-2 bg-cyan-700/40 text-cyan-300 rounded-lg text-sm hover:bg-cyan-700/60 transition-colors">
              Generate Playbook
            </button>
          </div>
        ))}
        {active.length === 0 && <p className="text-gray-500">All threats remediated! ✅</p>}
      </div>
    </div>
  );
}
