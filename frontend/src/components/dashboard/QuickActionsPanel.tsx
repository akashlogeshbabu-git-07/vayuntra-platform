import { ShieldCheck, RefreshCw, Download } from 'lucide-react';
export function QuickActionsPanel() {
  return (
    <div className="flex gap-2 flex-wrap">
      <button className="flex items-center gap-2 px-4 py-2 bg-cyan-600 hover:bg-cyan-700 text-white rounded-lg text-sm font-medium transition-colors">
        <ShieldCheck size={16} /> Full Scan
      </button>
      <button className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm font-medium transition-colors">
        <RefreshCw size={16} /> Refresh
      </button>
      <button className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm font-medium transition-colors">
        <Download size={16} /> Export
      </button>
    </div>
  );
}
