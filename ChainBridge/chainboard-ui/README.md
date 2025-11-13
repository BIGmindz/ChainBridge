# ChainBridge Control Tower UI

A production-grade React + TypeScript + Vite web dashboard for governance-focused logistics and fintech payment oversight. This is **v1** of the ChainBridge Control Tower—a clean, exception-first dashboard designed to surface problems and payment state at a glance.

## 🎯 Vision

The Control Tower is built on three core principles:

1. **Exception-First**: Surface problems and risks before celebrating success metrics
2. **Governance-Focused**: Make risk scores, payment states, and proof/signature status immediately visible
3. **Clean, Not Cluttered**: Data-informed layouts with zero cruft; no "data museum" dashboards

## 🚀 Quick Start

### Prerequisites

- **Node.js 18+** (includes npm 9+)
- **Git** for version control

### Installation

```bash
# 1. Navigate to the project directory
cd chainboard-ui

# 2. Install dependencies
npm install

# 3. Start the development server
npm run dev

# 4. Open http://localhost:5173 in your browser
```

### Available Scripts

| Script | Purpose |
|--------|---------|
| `npm run dev` | Start Vite dev server with HMR (http://localhost:5173) |
| `npm run build` | Build for production (outputs to `dist/`) |
| `npm run preview` | Preview production build locally |
| `npm run lint` | Run ESLint on all TypeScript files |
| `npm run format` | Format code with Prettier |
| `npm run test` | Run unit tests with Vitest |

## 📁 Project Structure

```
chainboard-ui/
├── src/
│   ├── components/           # Reusable React components
│   │   ├── Layout.tsx        # Global shell (top bar, nav, main content)
│   │   ├── KPIStrip.tsx      # 4 vital signs cards (active shipments, on-time %, at-risk, payment holds)
│   │   ├── ExceptionsPanel.tsx    # Exception table with live filters
│   │   ├── ExceptionsTable.tsx    # Full-screen exceptions view with presets
│   │   ├── ShipmentDetailDrawer.tsx  # Side panel detail view
│   │   └── ShipmentsTable.tsx   # Full shipment manifest table
│   ├── pages/
│   │   ├── OverviewPage.tsx     # Dashboard home (KPI + exceptions + detail)
│   │   ├── ShipmentsPage.tsx    # Full shipment list
│   │   └── ExceptionsPage.tsx   # Full-screen exceptions view
│   ├── services/
│   │   └── api.ts           # Mock API client (easily swappable for real FastAPI)
│   ├── types/
│   │   └── index.ts         # TypeScript domain models
│   ├── utils/
│   │   └── formatting.ts    # Data formatting and utility functions
│   ├── App.tsx              # Main app with routing
│   ├── index.tsx            # React entry point
│   ├── index.css            # Global styles
│   └── vite-env.d.ts        # Vite environment variable types
├── public/                  # Static assets
├── index.html              # HTML entry point
├── vite.config.ts          # Vite build configuration
├── tsconfig.json           # TypeScript strict mode config
├── tailwind.config.js      # TailwindCSS custom colors
├── postcss.config.cjs      # PostCSS with Tailwind and Autoprefixer
├── vitest.config.ts        # Unit test configuration
├── .eslintrc.cjs           # ESLint rules
├── .prettierrc              # Code formatting rules
├── .env.example             # Environment variables template
├── .gitignore              # Git ignore rules
├── package.json            # Dependencies and npm scripts
└── README.md              # This file
```

## 🛠️ Technology Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Framework** | React | 18.2.0 | UI library with hooks |
| **Language** | TypeScript | 5.3.3 | Type-safe JavaScript |
| **Build Tool** | Vite | 5.0.7 | Blazing fast dev server & builds |
| **Styling** | TailwindCSS | 3.4.0 | Utility-first CSS |
| **Routing** | React Router | 6.20.0 | Client-side navigation |
| **Icons** | Lucide React | 0.306.0 | Consistent icon set |
| **Testing** | Vitest | 1.0.4 | Fast unit test framework |
| **Code Quality** | ESLint + Prettier | Latest | Linting and formatting |

## 📊 Core Domain Models

All types are defined in `src/types/index.ts`:

### Shipment
The central domain entity combining freight, risk assessment, payment schedule, and cryptographic proof data.

```typescript
interface Shipment {
  shipment_id: string;
  token_id: string;
  carrier: string;
  customer: string;
  origin: string;
  destination: string;
  current_status: ShipmentStatus;  // "pickup" | "in_transit" | "delivery" | "delayed" | "blocked" | "completed"
  events: ShipmentEvent[];
  risk: RiskAssessment;           // risk_score, risk_category, confidence
  payment_state: PaymentState;    // "not_started" | "in_progress" | "partially_paid" | "blocked" | "completed"
  payment_schedule: PaymentMilestone[];
  proofpack: ProofPackSummary;    // manifest_hash, signature_status
}
```

### RiskAssessment
Quantifies freight risk with 0-100 score, confidence, and recommended mitigation actions.

### PaymentMilestone
Tracks smart contract payment releases with percentage, status, and timestamp.

### ProofPackSummary
Records cryptographic proof of shipment including manifest hash and signature verification status.

### NetworkVitals
KPI data for the dashboard (active shipments, on-time %, at-risk count, payment hold count).

## 🎨 Design System

### Color Palette (Custom ChainBridge Brand)

```javascript
// tailwind.config.js
colors: {
  primary: { 50: '#f0f9ff', 500: '#0ea5e9', 600: '#0284c7', 900: '#0c2d6b' },  // Sky Blue
  success: { 50: '#f0fdf4', 500: '#22c55e', 600: '#16a34a', 900: '#14532d' },  // Green
  warning: { 50: '#fffbeb', 500: '#f59e0b', 600: '#d97706', 900: '#78350f' },  // Amber
  danger: { 50: '#fef2f2', 500: '#ef4444', 600: '#dc2626', 900: '#7f1d1d' },   // Red
}
```

- **Primary (Sky)**: Normal operations, active states
- **Success (Green)**: Completed, healthy metrics
- **Warning (Amber)**: Medium risk, caution state
- **Danger (Red)**: High risk, blocked state

### Typography

- **Headings**: 3xl (h1), 2xl (h2), xl (h3)
- **Body**: sm (14px), base (16px)
- **Utilities**: xs (12px), tiny (11px)
- **Font Family**: System UI stack for performance

## 🔌 API Integration

### Current: Dual-Layer API Architecture

The application implements a **factory pattern** that automatically switches between mock and real API clients based on configuration:

#### Architecture

```
┌─────────────────────────────────────────────┐
│  React Components                            │
│  (ShipmentDetailDrawer, etc.)               │
└────────────────┬────────────────────────────┘
                 │ imports apiClient
                 ▼
┌─────────────────────────────────────────────┐
│  API Factory (getApiClient())               │
│  - Checks VITE_USE_MOCKS env var           │
│  - Returns IApiClient implementation        │
└────────────────┬────────────────────────────┘
                 │
         ┌───────┴───────┐
         │               │
         ▼               ▼
    MockApiClient   RealApiClient
    (offline)       (FastAPI backend)
```

#### API Methods

Both clients implement the `IApiClient` interface with these methods:

```typescript
interface IApiClient {
  // Vitals and monitoring
  getNetworkVitals(): Promise<NetworkVitals>;

  // Shipment data
  getShipments(filters?: ShipmentFilters): Promise<Shipment[]>;
  getShipmentDetail(shipmentId: string): Promise<Shipment | null>;

  // Exception tracking
  getExceptions(filters?: ExceptionFilters): Promise<ExceptionRow[]>;

  // Proof packs (blockchain governance)
  getProofPack(packId: string): Promise<ProofPackResponse>;
  createProofPack(payload: CreateProofPackPayload): Promise<ProofPackResponse>;
}
```

#### Mock Data Service

The `MockApiClient` generates 50 realistic shipments with proper distributions:

```typescript
// src/services/api.ts
const apiClient = await apiClient.getShipments();
const detail = await apiClient.getShipmentDetail('ship_abc123');
const proof = await apiClient.getProofPack('pp_123');
```

#### Real Backend Integration (FastAPI)

The `RealApiClient` in `src/services/realApiClient.ts` makes HTTP calls to your backend:

```typescript
// Automatically activated when VITE_USE_MOCKS=false
class RealApiClient implements IApiClient {
  async getProofPack(packId: string): Promise<ProofPackResponse> {
    return await fetchJson<ProofPackResponse>(`/proofpacks/${packId}`);
  }

  async createProofPack(payload: CreateProofPackPayload): Promise<ProofPackResponse> {
    return await fetchJson<ProofPackResponse>("/proofpacks/run", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  // ... other methods
}
```

#### Switching Between Mock and Real

Configure in `.env.local`:

```bash
# Use real backend (default in production)
VITE_USE_MOCKS=false
VITE_API_BASE_URL=http://127.0.0.1:8000

# Use mock data (default for demos)
VITE_USE_MOCKS=true
```

No component changes needed—the factory handles it automatically.

## ⚙️ Environment Configuration

The application uses a centralized configuration system (`src/config/env.ts`) for environment-based behavior:

#### Environment Variables

Create a `.env.local` file in the project root:

```bash
# Backend API Configuration
VITE_API_BASE_URL=http://127.0.0.1:8000    # FastAPI backend URL
VITE_USE_MOCKS=false                        # true = offline mock data, false = real API

# Environment Label (optional)
VITE_ENVIRONMENT_LABEL=sandbox              # "sandbox", "staging", or "production"
```

#### Environment Label Auto-Detection

If `VITE_ENVIRONMENT_LABEL` is not set, the system auto-detects from the URL:

```typescript
// src/config/env.ts
if (url.includes('localhost')) return 'Sandbox';
if (url.includes('staging')) return 'Staging';
if (url.includes('prod')) return 'Production';
return 'Custom';
```

The label displays in the top navigation bar to prevent accidental API calls to the wrong environment.

#### Configuration Object

Access environment config from any component:

```typescript
import { config } from "../config/env";

console.log(config.apiBaseUrl);     // "http://127.0.0.1:8000"
console.log(config.useMocks);       // false
console.log(config.environmentLabel); // "Sandbox"
console.log(config.isDevelopment);  // true (in dev server)
console.log(config.isProduction);   // false
```

## 🧪 Testing

Unit tests validate critical utility functions and component rendering:

```bash
# Run all tests
npm run test

# Run tests with coverage
npm run test:coverage

# Watch mode (re-run on file changes)
npm run test:watch
```

**Test files:**
- `src/utils/formatting.test.ts` - Utility function tests
- `src/components/*.test.tsx` - Component snapshot & behavior tests

## 📦 Build & Deployment

### Development Build
```bash
npm run dev
```
- Starts Vite dev server at http://localhost:5173
- Hot Module Replacement (HMR) enabled
- Full source maps for debugging

### Production Build
```bash
npm run build
```
- TypeScript type checking
- Minification and code splitting
- Output: `dist/` folder (ready for static hosting)
- Size: ~194KB gzipped (60KB JS + 4KB CSS)

### Preview Production Build Locally
```bash
npm run preview
```
- Serves the `dist/` folder locally for testing before deployment

## 🚢 Deployment

The `dist/` folder can be deployed to any static hosting:

### Vercel (Recommended)
```bash
npm install -g vercel
vercel --prod
```

### Netlify
```bash
npm install -g netlify-cli
netlify deploy --prod --dir=dist
```

### AWS S3 + CloudFront
```bash
aws s3 sync dist/ s3://your-bucket --delete
```

### Docker
```dockerfile
FROM node:18-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## 🛣️ Routing Map

| Path | Component | Purpose |
|------|-----------|---------|
| `/` | OverviewPage | Dashboard home—KPI strip, exceptions panel, shipment detail drawer |
| `/shipments` | ShipmentsPage | Full shipment manifest with filtering |
| `/exceptions` | ExceptionsPage | Full-screen exceptions view with saved presets |
| *(Future)* `/risk` | RiskAnalysisPage | Risk analytics and trending |
| *(Future)* `/payments` | PaymentsPage | Payment milestone tracking |

## 🎯 Features by Page

### Overview Page (`/`)
**The executive dashboard.**
- **KPI Strip**: 4 vital signs (active shipments, on-time %, at-risk, payment holds)
- **Exceptions Panel**: Live exceptions table with risk, payment state, age filters
- **Detail Drawer**: Click a row to see full shipment details (events, risk, payment schedule, proofs)

### Shipments Page (`/shipments`)
**Full shipment manifest.**
- Tabular view of all shipments
- Columns: ID, Carrier, Customer, Lane, Status, Risk Score, Payment State, Payment Progress %
- Hover effects and color-coded risk/payment state
- *(Future)* Sorting, filtering, bulk actions

### Exceptions Page (`/exceptions`)
**Deep-dive exception analysis.**
- Same table as ExceptionsPanel but full-screen
- **Saved Views**:
  - "All Exceptions" - unfiltered
  - "Ops View" - late pickups/deliveries
  - "Finance View" - payment blocks
  - "High Risk" - risk score >70
- **CSV Export**: Download filtered data for external analysis
- *(Future)* Saved filters, annotations, audit trail

## 🔄 Data Flow

```
┌─────────────────────────────────────────┐
│ Page Component (OverviewPage, etc.)     │
│ - useEffect() fetches from apiClient    │
│ - useState() for local data             │
└──────────────┬──────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│ apiClient (src/services/api.ts)          │
│ - MockApiClient (currently)              │
│ - Will become HTTP client later          │
│ - 200-300ms delay simulation             │
└──────────────┬───────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│ Data → Component Props                   │
│ - Fully typed (TypeScript)               │
│ - formatRiskScore(), formatUSD(), etc.   │
└──────────────┬───────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│ UI Components (KPIStrip, Table, etc.)    │
│ - Pure functional components             │
│ - TailwindCSS styling                    │
│ - Lucide icons                           │
└──────────────────────────────────────────┘
```

## 🐛 Troubleshooting

### Dev Server Won't Start
```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### Import Errors in IDE
```bash
# Ensure TypeScript is strict mode
npm run build  # This will show type errors
```

### HMR Not Working
- Check that your firewall allows localhost:5173
- Restart the dev server: `Ctrl+C`, then `npm run dev`

### ESLint Warnings
```bash
npm run lint              # Check all files
npm run format            # Auto-fix formatting
```

## 📚 Code Style

This project enforces:

- **TypeScript**: Strict mode, no `any` types
- **ESLint**: React hooks, code quality rules
- **Prettier**: 100-char line width, 2-space indent, semicolons required
- **Naming**: camelCase for variables, PascalCase for components/interfaces

Example:
```typescript
// ✅ Good
interface ShipmentCardProps {
  shipment: Shipment;
  onSelect: (id: string) => void;
}

export function ShipmentCard({ shipment, onSelect }: ShipmentCardProps): JSX.Element {
  const riskColor = shipment.risk.risk_category === "high" ? "text-danger-600" : "text-success-600";
  return <div onClick={() => onSelect(shipment.shipment_id)} className={riskColor}>...</div>;
}

// ❌ Bad
function ShipmentCard(props: any) {
  let color = props.shipment.risk.high ? 'red' : 'green'
  return <div onClick={() => props.onSelect(props.shipment.shipment_id)} className={color}>...</div>
}
```

## 🔐 Security Notes

- **No secrets in code**: All API URLs and environment values via `.env`
- **XSS protection**: React auto-escapes by default; sanitize user input if needed
- **CORS**: Configure your FastAPI backend with appropriate CORS headers
- **HTTPS**: Always use HTTPS in production

## 📖 Resources

- [React Docs](https://react.dev)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [Vite Guide](https://vitejs.dev/guide/)
- [TailwindCSS Docs](https://tailwindcss.com/docs)
- [React Router Docs](https://reactrouter.com/)

## 🤝 Contributing

1. Create a feature branch: `git checkout -b feat/my-feature`
2. Make changes and test: `npm run lint && npm run build`
3. Commit with clear message: `git commit -m "feat: add new feature"`
4. Push and create a pull request

## 📄 License

Copyright © 2025 ChainBridge. All rights reserved.

---

**Next Steps:**

- [ ] Integrate with real ChainFreight API
- [ ] Integrate with real ChainPay API
- [ ] Integrate with real ChainIQ risk engine
- [ ] Add user authentication
- [ ] Add saved filters and views
- [ ] Add audit logging
- [ ] Add accessibility audit (WCAG AA)
- [ ] Deploy to production

**Questions?** Check the [ARCHITECTURE.md](../ARCHITECTURE.md) for backend integration details.
