/**
 * KeyboardHintsFooter - Keyboard shortcut reference
 *
 * Simplified, calm design - only essential hints shown.
 * Reduces cognitive load while maintaining discoverability.
 */

export function KeyboardHintsFooter() {
  // Only show essential navigation hints - more discoverable via ?/Help
  const hints = [
    { keys: ["↑", "↓"], label: "Navigate" },
    { keys: ["Enter"], label: "Select" },
    { keys: ["E"], label: "Export" },
    { keys: ["?"], label: "All shortcuts" },
  ];

  return (
    <div className="bg-slate-900/60 border-t border-slate-800/50 px-6 py-2.5">
      <div className="flex items-center gap-8 justify-center">
        {hints.map((hint, index) => (
          <div key={index} className="flex items-center gap-2 opacity-60 hover:opacity-100 transition-opacity duration-200">
            <div className="flex items-center gap-1">
              {hint.keys.map((key, keyIndex) => (
                <kbd
                  key={keyIndex}
                  className="px-2 py-0.5 text-xs font-mono bg-slate-800/80 text-slate-400 border border-slate-700/50 rounded"
                >
                  {key}
                </kbd>
              ))}
            </div>
            <span className="text-xs text-slate-500">{hint.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
