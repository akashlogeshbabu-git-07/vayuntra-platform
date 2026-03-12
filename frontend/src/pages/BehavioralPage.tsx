import { Brain } from 'lucide-react';
export function BehavioralPage() {
  return (
    <div className="p-6 bg-gray-950 min-h-screen">
      <h1 className="text-2xl font-bold text-white flex items-center gap-3 mb-6"><Brain className="text-purple-400" size={24} />Behavioral Memory</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[{ label: 'Profiles Tracked', value: 5, color: 'cyan' }, { label: 'Anomalies Learned', value: 15, color: 'red' }, { label: 'Baseline Days', value: 7, color: 'green' }].map(card => (
          <div key={card.label} className="bg-gray-900 rounded-xl border border-gray-800 p-5 text-center">
            <p className="text-3xl font-bold text-white mb-1">{card.value}</p>
            <p className="text-gray-400 text-sm">{card.label}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
