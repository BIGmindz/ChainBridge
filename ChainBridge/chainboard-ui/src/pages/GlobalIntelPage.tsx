export default function GlobalIntelPage(): JSX.Element {
  return (
    <div className="flex h-full items-center justify-center p-6">
      <div className="rounded-2xl border border-slate-700 bg-slate-900/70 p-6 text-center shadow-2xl">
        <p className="text-xs uppercase tracking-[0.4em] text-slate-500">SONNY PAC</p>
        <h1 className="mt-4 text-3xl font-semibold text-white">Global Intelligence</h1>
        <p className="mt-2 text-sm text-slate-400">
          Interactive console is loading new intelligence feeds...
        </p>
      </div>
    </div>
  );
}
