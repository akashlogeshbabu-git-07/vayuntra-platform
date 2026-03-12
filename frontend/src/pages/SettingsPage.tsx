import { Settings } from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';
export function SettingsPage() {
  const { user } = useAuth();
  return (
    <div className="p-6 bg-gray-950 min-h-screen">
      <h1 className="text-2xl font-bold text-white flex items-center gap-3 mb-6"><Settings className="text-gray-400" size={24} />Settings</h1>
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-5 max-w-md">
        <h2 className="text-sm font-semibold text-gray-300 mb-4">Account</h2>
        <div className="space-y-3 text-sm">
          <div className="flex justify-between"><span className="text-gray-500">Email</span><span className="text-white">{user?.email}</span></div>
          <div className="flex justify-between"><span className="text-gray-500">Role</span><span className="text-white capitalize">{user?.role?.replace('_', ' ')}</span></div>
          <div className="flex justify-between"><span className="text-gray-500">Tenant ID</span><span className="text-white font-mono text-xs">{user?.tenant_id?.slice(0, 8)}...</span></div>
        </div>
      </div>
    </div>
  );
}
