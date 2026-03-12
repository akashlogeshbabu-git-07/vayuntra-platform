export function LoadingScreen() {
  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center">
      <div className="text-center">
        <div className="w-16 h-16 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-cyan-400 text-lg font-semibold">Vayuntra</p>
        <p className="text-gray-500 text-sm">Loading control plane...</p>
      </div>
    </div>
  );
}
