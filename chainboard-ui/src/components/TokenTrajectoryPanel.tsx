import React from 'react';
import { useEventBusStore } from '../state/eventBusStore';

// Simple sparkline/histogram for token trajectory
function getColor(trend: number) {
  if (trend > 0) return '#22c55e'; // green
  if (trend < 0) return '#ef4444'; // red
  return '#3b82f6'; // blue
}

export default function TokenTrajectoryPanel() {
  // For demo, use first shipment with events
  const tokenEvents = useEventBusStore((s) => s.tokenEvents);
  const shipmentId = tokenEvents[0]?.canonical_shipment_id;
  const trajectory = shipmentId ? useEventBusStore.getState().getTokenTrajectory(shipmentId) : [];

  if (!shipmentId || trajectory.length === 0) {
    return (
      <div className="flex flex-col gap-3 p-4 bg-neutral-900/40 rounded-xl shadow-lg">
        <h2 className="text-lg font-bold mb-2 text-white">Token Trajectory</h2>
        <div className="text-gray-400">No token trajectory data yet.</div>
      </div>
    );
  }

  // SVG dimensions
  const width = 320;
  const height = 80;
  const maxY = Math.max(...trajectory.map((p) => p.y), 1);
  const minY = Math.min(...trajectory.map((p) => p.y), 0);
  const points = trajectory.map((p, i) => {
    const x = (i / (trajectory.length - 1 || 1)) * (width - 20) + 10;
    const y = height - ((p.y - minY) / (maxY - minY || 1)) * (height - 20) - 10;
    return `${x},${y}`;
  }).join(' ');

  // Color trend
  const trend = trajectory[trajectory.length - 1].y - trajectory[0].y;
  const color = getColor(trend);

  return (
    <div className="flex flex-col gap-3 p-4 bg-neutral-900/40 rounded-xl shadow-lg">
      <h2 className="text-lg font-bold mb-2 text-white">Token Trajectory</h2>
      <svg width={width} height={height} className="w-full h-20">
        <polyline
          fill="none"
          stroke={color}
          strokeWidth="3"
          points={points}
        />
        {trajectory.map((p, i) => {
          const x = (i / (trajectory.length - 1 || 1)) * (width - 20) + 10;
          const y = height - ((p.y - minY) / (maxY - minY || 1)) * (height - 20) - 10;
          return (
            <circle
              key={i}
              cx={x}
              cy={y}
              r={p.burn ? 5 : 3}
              fill={p.burn ? '#ef4444' : color}
              opacity={p.burn ? 0.8 : 1}
            />
          );
        })}
      </svg>
      <div className="text-xs text-white mt-2">
        <span className="font-bold">Cumulative Net Token:</span> {trajectory[trajectory.length - 1].y.toFixed(2)}
        <span className="ml-4 font-bold">Trend:</span> <span style={{ color }}>{trend > 0 ? '↑ Positive' : trend < 0 ? '↓ Negative' : '→ Stable'}</span>
      </div>
    </div>
  );
}
