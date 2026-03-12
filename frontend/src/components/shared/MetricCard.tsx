import { LucideIcon } from 'lucide-react';
interface Props {
  title: string; value: string | number; subtitle?: string;
  icon?: LucideIcon; color?: string; trend?: 'up' | 'down' | 'neutral'; isLoading?: boolean;
}
export function MetricCard({ title, value, subtitle, icon: Icon, color = 'cyan', isLoading }: Props) {
  const colors: Record<string, string> = {
    cyan: 'text-cyan-400 bg-cyan-900/20 border-cyan-800/50',
    red: 'text-red-400 bg-red-900/20 border-red-800/50',
    yellow: 'text-yellow-400 bg-yellow-900/20 border-yellow-800/50',
    green: 'text-green-400 bg-green-900/20 border-green-800/50',
    purple: 'text-purple-400 bg-purple-900/20 border-purple-800/50',
    orange: 'text-orange-400 bg-orange-900/20 border-orange-800/50',
  };
  const cls = colors[color] || colors.cyan;
  return (
    <div className={`rounded-xl border p-5 ${cls}`}>
      <div className="flex items-center justify-between mb-3">
        <span className="text-gray-400 text-sm font-medium">{title}</span>
        {Icon && <Icon size={20} className="opacity-70" />}
      </div>
      {isLoading ? (
        <div className="h-8 bg-gray-700 rounded animate-pulse w-16" />
      ) : (
        <div className="text-3xl font-bold text-white">{value}</div>
      )}
      {subtitle && <p className="text-xs text-gray-500 mt-1">{subtitle}</p>}
    </div>
  );
}
