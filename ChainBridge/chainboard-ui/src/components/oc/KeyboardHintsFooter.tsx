/**
 * KeyboardHintsFooter - Keyboard shortcut reference
 *
 * Displays available keyboard shortcuts at the bottom of Operator Console.
 */

export function KeyboardHintsFooter() {
  const hints = [
    { keys: ["↑", "↓"], label: "Navigate" },
    { keys: ["J", "K"], label: "Navigate (Vim)" },
    { keys: ["Enter"], label: "Select" },
    { keys: ["E"], label: "Export" },
    { keys: ["Space"], label: "Multi-select" },
    { keys: ["⇧", "E"], label: "Bulk Export" },
    { keys: ["⌘", "K"], label: "Command Palette" },
  ];

  return (
    <div className="bg-slate-900/80 border-t border-slate-800 px-6 py-2">
      <div className="flex items-center gap-6 justify-center">
        {hints.map((hint, index) => (
          <div key={index} className="flex items-center gap-2">
            <div className="flex items-center gap-1">
              {hint.keys.map((key, keyIndex) => (
                <kbd
                  key={keyIndex}
                  className="px-2 py-0.5 text-xs font-mono bg-slate-800 text-slate-300 border border-slate-700 rounded"
                >
                  {key}
                </kbd>
              ))}
            </div>
            <span className="text-xs text-slate-400">{hint.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
