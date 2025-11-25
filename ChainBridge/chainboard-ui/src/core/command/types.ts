/**
 * Command Palette Types
 *
 * Keyboard shortcuts and command definitions for operator console.
 */

export type CommandId =
  | "nav:overview"
  | "nav:shipments"
  | "nav:sandbox"
  | "nav:triage"
  | "triage:my_alerts"
  | "demo:start_investor";

export interface CommandItem {
  id: CommandId;
  label: string;
  shortcut?: string;
}
