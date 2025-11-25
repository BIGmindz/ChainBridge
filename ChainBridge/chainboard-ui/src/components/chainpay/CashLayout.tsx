/**
 * CashLayout - Clean Layout for ChainPay Cash View
 *
 * Investor-friendly interface for payment intent management.
 * Simpler than OC layout - focused on cash/settlement operations.
 */

import { APIHealthIndicator } from "../settlements/APIHealthIndicator";

interface CashLayoutProps {
  children: React.ReactNode;
  filterBar?: React.ReactNode; // Optional filter controls
}

export function CashLayout({ children, filterBar }: CashLayoutProps) {
  return (
    <div className="h-screen bg-slate-950 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="bg-slate-900/80 border-b border-slate-800 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">💰 ChainPay — Cash View</h1>
            <p className="text-sm text-slate-400">Payment intent management & settlement tracking</p>
          </div>
          <APIHealthIndicator />
        </div>

        {/* Filter Bar */}
        {filterBar && (
          <div className="mt-4">
            {filterBar}
          </div>
        )}
      </div>

      {/* Main Content */}
      <div className="flex flex-col flex-1 overflow-hidden gap-4 p-6">
        {children}
      </div>
    </div>
  );
}
