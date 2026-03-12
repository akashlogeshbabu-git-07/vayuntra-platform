import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { Shield, AlertTriangle, Server, Activity, Brain, Settings, LogOut, BarChart2 } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';

const nav = [
  { to: '/dashboard', icon: BarChart2, label: 'Dashboard' },
  { to: '/threats', icon: AlertTriangle, label: 'Threats' },
  { to: '/agents', icon: Server, label: 'Agents' },
  { to: '/behavioral', icon: Brain, label: 'Behavioral' },
  { to: '/remediation', icon: Activity, label: 'Remediation' },
  { to: '/settings', icon: Settings, label: 'Settings' },
];

export function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const handleLogout = () => { logout(); navigate('/login'); };
  return (
    <div className="flex h-screen bg-gray-950 text-gray-100 overflow-hidden">
      {/* Sidebar */}
      <aside className="w-16 lg:w-60 bg-gray-900 border-r border-gray-800 flex flex-col py-4 shrink-0">
        <div className="flex items-center gap-3 px-4 mb-8">
          <Shield className="text-cyan-400 shrink-0" size={28} />
          <span className="hidden lg:block font-bold text-white text-lg">Vayuntra</span>
        </div>
        <nav className="flex-1 space-y-1 px-2">
          {nav.map(({ to, icon: Icon, label }) => (
            <NavLink key={to} to={to} className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                isActive ? 'bg-cyan-900/40 text-cyan-400' : 'text-gray-400 hover:text-white hover:bg-gray-800'
              }`
            }>
              <Icon size={18} className="shrink-0" />
              <span className="hidden lg:block">{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="px-2 border-t border-gray-800 pt-3 mt-3">
          <div className="flex items-center gap-3 px-3 py-2 mb-1">
            <div className="w-7 h-7 rounded-full bg-cyan-600 flex items-center justify-center text-xs font-bold shrink-0">
              {user?.email?.[0].toUpperCase()}
            </div>
            <div className="hidden lg:block overflow-hidden">
              <p className="text-xs font-medium text-white truncate">{user?.email}</p>
              <p className="text-xs text-gray-500 capitalize">{user?.role}</p>
            </div>
          </div>
          <button onClick={handleLogout} className="flex items-center gap-3 px-3 py-2 w-full rounded-lg text-sm text-gray-400 hover:text-red-400 hover:bg-gray-800 transition-colors">
            <LogOut size={18} className="shrink-0" />
            <span className="hidden lg:block">Logout</span>
          </button>
        </div>
      </aside>
      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
}
