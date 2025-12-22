export interface IoTDeviceHealth {
  id: string;
  name: string;
  status: string;
  last_heartbeat: string;
  risk_score: number;
  // Optional model confidence for this device's signal (0..1)
  signal_confidence?: number;
}

export interface IoTHealthResponse {
  devices: IoTDeviceHealth[];
}
