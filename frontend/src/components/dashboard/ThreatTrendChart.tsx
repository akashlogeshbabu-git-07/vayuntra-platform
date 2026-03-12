import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
export function ThreatTrendChart({ trend }: { trend?: Array<{ hour: number; count: number }> }) {
  const data = (trend || []).slice().reverse().map((d) => ({ name: `${d.hour}h`, threats: d.count }));
  return (
    <ResponsiveContainer width="100%" height={120}>
      <AreaChart data={data}>
        <defs>
          <linearGradient id="tg" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
          </linearGradient>
        </defs>
        <XAxis dataKey="name" tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={false} tickLine={false} />
        <YAxis hide />
        <Tooltip contentStyle={{ backgroundColor: '#111827', border: '1px solid #1f2937', borderRadius: 8 }} labelStyle={{ color: '#9ca3af' }} itemStyle={{ color: '#06b6d4' }} />
        <Area type="monotone" dataKey="threats" stroke="#06b6d4" fill="url(#tg)" strokeWidth={2} dot={false} />
      </AreaChart>
    </ResponsiveContainer>
  );
}
