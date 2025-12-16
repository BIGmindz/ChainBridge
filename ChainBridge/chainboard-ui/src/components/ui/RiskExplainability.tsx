/**
 * 🩵🩵🩵🩵🩵🩵🩵🩵🩵🩵
 * LIRA — GID-09 — EXPERIENCE ENGINEER
 * Risk Explainability Components — ChainBoard UI
 * 🩵🩵🩵🩵🩵🩵🩵🩵🩵🩵
 *
 * Components for explaining ChainIQ risk scores and feature attributions
 * to operators. Implements ML explainability patterns with Calm UX.
 */

import { classNames } from '../../utils/classNames';
import {
  getStatusClasses,
  scoreToRiskTier,
  getRiskTierConfig,
  type RiskTier,
} from './design-tokens';

// =============================================================================
// TYPE DEFINITIONS
// =============================================================================

export interface FeatureAttribution {
  /** Feature name */
  feature: string;
  /** Contribution to risk score (-100 to +100) */
  contribution: number;
  /** Human-readable description */
  description?: string;
}

export interface RiskExplanation {
  /** Overall risk score (0-100) */
  score: number;
  /** Risk tier */
  tier: RiskTier;
  /** Summary explanation */
  summary: string;
  /** Top contributing features */
  features: FeatureAttribution[];
  /** Model version used */
  modelVersion?: string;
  /** Timestamp of assessment */
  assessedAt?: string;
}

// =============================================================================
// RISK SCORE GAUGE — Visual score indicator
// =============================================================================

export interface RiskScoreGaugeProps {
  /** Risk score (0-100) */
  score: number;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Show numeric score */
  showScore?: boolean;
  /** Show risk tier label */
  showTier?: boolean;
}

export function RiskScoreGauge({
  score,
  size = 'md',
  showScore = true,
  showTier = true,
}: RiskScoreGaugeProps) {
  const tier = scoreToRiskTier(score);
  const config = getRiskTierConfig(tier);
  const colors = getStatusClasses(config.color);

  const sizeClasses = {
    sm: 'h-16 w-16 text-lg',
    md: 'h-24 w-24 text-2xl',
    lg: 'h-32 w-32 text-3xl',
  };

  // Calculate stroke dash for circular progress
  const radius = 45;
  const circumference = 2 * Math.PI * radius;
  const progress = (score / 100) * circumference;

  return (
    <div
      className="flex flex-col items-center gap-2"
      data-testid="risk-score-gauge"
    >
      <div className={classNames('relative', sizeClasses[size])}>
        <svg className="h-full w-full -rotate-90" viewBox="0 0 100 100">
          {/* Background circle */}
          <circle
            cx="50"
            cy="50"
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth="8"
            className="text-gray-200"
          />
          {/* Progress circle */}
          <circle
            cx="50"
            cy="50"
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={circumference - progress}
            className={colors.text}
          />
        </svg>
        {showScore && (
          <span
            className={classNames(
              'absolute inset-0 flex items-center justify-center font-bold',
              colors.text
            )}
          >
            {score}
          </span>
        )}
      </div>
      {showTier && (
        <span className={classNames('text-sm font-medium', colors.text)}>
          {config.label}
        </span>
      )}
    </div>
  );
}

// =============================================================================
// FEATURE CONTRIBUTION BAR — Shows feature impact on score
// =============================================================================

export interface FeatureContributionBarProps {
  /** Feature attribution data */
  feature: FeatureAttribution;
  /** Max contribution for scaling */
  maxContribution?: number;
}

export function FeatureContributionBar({
  feature,
  maxContribution = 100,
}: FeatureContributionBarProps) {
  const isPositive = feature.contribution >= 0;
  const absContribution = Math.abs(feature.contribution);
  const widthPercent = (absContribution / maxContribution) * 100;

  const barColor = isPositive ? 'bg-red-500' : 'bg-green-500';
  const textColor = isPositive ? 'text-red-700' : 'text-green-700';

  return (
    <div
      className="flex items-center gap-3"
      data-testid="feature-contribution-bar"
    >
      <div className="w-32 truncate text-sm font-medium text-gray-700">
        {feature.feature}
      </div>
      <div className="flex-1">
        <div className="flex h-4 items-center">
          {/* Center line */}
          <div className="w-1/2">
            {!isPositive && (
              <div className="flex justify-end">
                <div
                  className={classNames('h-3 rounded-l', barColor)}
                  style={{ width: `${widthPercent}%` }}
                />
              </div>
            )}
          </div>
          <div className="h-full w-px bg-gray-400" />
          <div className="w-1/2">
            {isPositive && (
              <div
                className={classNames('h-3 rounded-r', barColor)}
                style={{ width: `${widthPercent}%` }}
              />
            )}
          </div>
        </div>
      </div>
      <div className={classNames('w-12 text-right text-sm font-medium', textColor)}>
        {isPositive ? '+' : ''}{feature.contribution}
      </div>
    </div>
  );
}

// =============================================================================
// RISK EXPLANATION CARD — Full explainability panel
// =============================================================================

export interface RiskExplanationCardProps {
  /** Risk explanation data */
  explanation: RiskExplanation;
  /** Number of top features to show */
  maxFeatures?: number;
  /** Show model metadata */
  showMetadata?: boolean;
}

export function RiskExplanationCard({
  explanation,
  maxFeatures = 5,
  showMetadata = false,
}: RiskExplanationCardProps) {
  const config = getRiskTierConfig(explanation.tier);
  const colors = getStatusClasses(config.color);
  const topFeatures = explanation.features.slice(0, maxFeatures);
  const maxContribution = Math.max(
    ...topFeatures.map((f) => Math.abs(f.contribution)),
    1
  );

  return (
    <div
      className={classNames(
        'rounded-lg border p-4',
        colors.border
      )}
      data-testid="risk-explanation-card"
    >
      <div className="flex items-start gap-4">
        <RiskScoreGauge score={explanation.score} size="md" showTier={false} />
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h3 className="text-lg font-semibold">{config.label}</h3>
            <span className={classNames('text-sm', colors.text)}>
              Score: {explanation.score}/100
            </span>
          </div>
          <p className="mt-1 text-sm text-gray-600">{explanation.summary}</p>
        </div>
      </div>

      {topFeatures.length > 0 && (
        <div className="mt-4 space-y-2">
          <h4 className="text-sm font-medium text-gray-700">
            Top Contributing Factors
          </h4>
          {topFeatures.map((feature, index) => (
            <FeatureContributionBar
              key={index}
              feature={feature}
              maxContribution={maxContribution}
            />
          ))}
        </div>
      )}

      {showMetadata && (explanation.modelVersion || explanation.assessedAt) && (
        <div className="mt-4 flex gap-4 border-t pt-3 text-xs text-gray-500">
          {explanation.modelVersion && (
            <span>Model: {explanation.modelVersion}</span>
          )}
          {explanation.assessedAt && (
            <span>Assessed: {explanation.assessedAt}</span>
          )}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// RISK SUMMARY STRIP — Compact horizontal risk summary
// =============================================================================

export interface RiskSummaryStripProps {
  /** Risk score (0-100) */
  score: number;
  /** Brief summary text */
  summary?: string;
  /** Show gauge */
  showGauge?: boolean;
}

export function RiskSummaryStrip({
  score,
  summary,
  showGauge = true,
}: RiskSummaryStripProps) {
  const tier = scoreToRiskTier(score);
  const config = getRiskTierConfig(tier);
  const colors = getStatusClasses(config.color);

  return (
    <div
      className={classNames(
        'flex items-center gap-3 rounded-md border px-3 py-2',
        colors.border,
        colors.bg
      )}
      data-testid="risk-summary-strip"
    >
      {showGauge && <RiskScoreGauge score={score} size="sm" showTier={false} />}
      <div className="flex-1">
        <span className={classNames('font-medium', colors.text)}>
          {config.label}
        </span>
        {summary && (
          <p className="text-sm text-gray-600">{summary}</p>
        )}
      </div>
    </div>
  );
}
