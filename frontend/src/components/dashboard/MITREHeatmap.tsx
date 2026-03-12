const TACTICS = ['Initial Access','Execution','Persistence','Privilege Escalation','Defense Evasion','Credential Access','Discovery','Lateral Movement','Exfiltration','Impact'];
export function MITREHeatmap({ breakdown }: { breakdown?: Record<string, number> }) {
  const max = Math.max(...Object.values(breakdown || {}), 1);
  return (
    <div className="grid grid-cols-5 gap-1.5">
      {TACTICS.map((t) => {
        const count = breakdown?.[t] || 0;
        const intensity = count / max;
        return (
          <div key={t} title={`${t}: ${count}`} className="rounded p-2 text-center cursor-default"
            style={{ backgroundColor: `rgba(6, 182, 212, ${0.05 + intensity * 0.6})`, border: `1px solid rgba(6, 182, 212, ${0.1 + intensity * 0.4})` }}>
            <p className="text-xs text-gray-300 leading-tight">{t.split(' ').slice(-1)[0]}</p>
            <p className="text-sm font-bold text-white">{count}</p>
          </div>
        );
      })}
    </div>
  );
}
