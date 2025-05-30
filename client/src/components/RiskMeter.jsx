import React from 'react';

const RiskMeter = ({ riskScore, size = 'md', showLabel = true, className = '' }) => {
  // Handle null/undefined risk scores
  if (riskScore === null || riskScore === undefined) {
    return (
      <div className={`flex items-center justify-center ${className}`}>
        <div className={`${getSizeClasses(size)} bg-zinc-800 rounded-lg border border-zinc-700 flex items-center justify-center`}>
          <span className="text-xs text-zinc-500">N/A</span>
        </div>
      </div>
    );
  }

  const score = parseFloat(riskScore);
  const percentage = ((score - 1) / 9) * 100; // Convert 1-10 scale to 0-100%
  
  // Risk level configuration
  const getRiskConfig = (score) => {
    if (score <= 2.0) {
      return { 
        level: 'Very Low', 
        color: 'from-emerald-500 to-green-400',
        bgColor: 'bg-emerald-500/10',
        textColor: 'text-emerald-400',
        borderColor: 'border-emerald-500/30'
      };
    } else if (score <= 3.5) {
      return { 
        level: 'Low', 
        color: 'from-green-500 to-lime-400',
        bgColor: 'bg-green-500/10',
        textColor: 'text-green-400',
        borderColor: 'border-green-500/30'
      };
    } else if (score <= 5.0) {
      return { 
        level: 'Medium', 
        color: 'from-yellow-500 to-amber-400',
        bgColor: 'bg-yellow-500/10',
        textColor: 'text-yellow-400',
        borderColor: 'border-yellow-500/30'
      };
    } else if (score <= 7.0) {
      return { 
        level: 'High', 
        color: 'from-orange-500 to-red-400',
        bgColor: 'bg-orange-500/10',
        textColor: 'text-orange-400',
        borderColor: 'border-orange-500/30'
      };
    } else if (score <= 8.5) {
      return { 
        level: 'Very High', 
        color: 'from-red-500 to-rose-400',
        bgColor: 'bg-red-500/10',
        textColor: 'text-red-400',
        borderColor: 'border-red-500/30'
      };
    } else {
      return { 
        level: 'Extreme', 
        color: 'from-red-600 to-pink-500',
        bgColor: 'bg-red-600/10',
        textColor: 'text-red-400',
        borderColor: 'border-red-600/30'
      };
    }
  };

  const config = getRiskConfig(score);

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      {/* Risk Score Meter */}
      <div className={`relative ${getSizeClasses(size)} ${config.bgColor} ${config.borderColor} border rounded-lg overflow-hidden`}>
        {/* Background track */}
        <div className="absolute inset-0 bg-zinc-800/50"></div>
        
        {/* Progress fill with gradient */}
        <div 
          className={`absolute inset-0 bg-gradient-to-r ${config.color} transition-all duration-700 ease-out`}
          style={{ 
            width: `${percentage}%`,
            background: `linear-gradient(90deg, ${getGradientStops(config.color)})`
          }}
        ></div>
        
        {/* Risk score text overlay */}
        <div className="relative z-10 h-full flex items-center justify-center">
          <span className={`font-bold ${getTextSize(size)} text-white drop-shadow-sm`}>
            {score.toFixed(1)}
          </span>
        </div>
        
        {/* Subtle inner glow effect */}
        <div className={`absolute inset-0 bg-gradient-to-r ${config.color} opacity-20 blur-sm`}
             style={{ width: `${percentage}%` }}></div>
      </div>

      {/* Risk level label */}
      {showLabel && (
        <div className="flex flex-col">
          <span className={`text-xs font-medium ${config.textColor}`}>
            {config.level}
          </span>
          <span className="text-xs text-zinc-500">
            Risk
          </span>
        </div>
      )}
    </div>
  );
};

// Helper functions
function getSizeClasses(size) {
  switch (size) {
    case 'sm':
      return 'w-12 h-5';
    case 'md':
      return 'w-16 h-6';
    case 'lg':
      return 'w-20 h-8';
    case 'xl':
      return 'w-24 h-10';
    default:
      return 'w-16 h-6';
  }
}

function getTextSize(size) {
  switch (size) {
    case 'sm':
      return 'text-xs';
    case 'md':
      return 'text-sm';
    case 'lg':
      return 'text-base';
    case 'xl':
      return 'text-lg';
    default:
      return 'text-sm';
  }
}

function getGradientStops(colorClass) {
  const gradients = {
    'from-emerald-500 to-green-400': '#10b981, #4ade80',
    'from-green-500 to-lime-400': '#22c55e, #a3e635',
    'from-yellow-500 to-amber-400': '#eab308, #fbbf24',
    'from-orange-500 to-red-400': '#f97316, #f87171',
    'from-red-500 to-rose-400': '#ef4444, #fb7185',
    'from-red-600 to-pink-500': '#dc2626, #ec4899'
  };
  return gradients[colorClass] || '#6b7280, #9ca3af';
}

// Tooltip component for detailed risk breakdown
export const RiskTooltip = ({ riskScore, riskComponents, className = '' }) => {
  if (!riskScore || !riskComponents) return null;

  const config = getRiskConfig(riskScore);
  
  return (
    <div className={`p-3 bg-zinc-900 border border-zinc-700 rounded-lg shadow-lg ${className}`}>
      <div className="flex items-center gap-2 mb-2">
        <RiskMeter riskScore={riskScore} size="sm" showLabel={false} />
        <div>
          <div className={`text-sm font-semibold ${config.textColor}`}>
            Risk Score: {riskScore.toFixed(1)}
          </div>
          <div className="text-xs text-zinc-400">
            {config.level} Risk
          </div>
        </div>
      </div>
      
      <div className="space-y-1 text-xs">
        <div className="grid grid-cols-2 gap-2">
          <div>Volatility: {riskComponents.volatility || 'N/A'}/10</div>
          <div>ATR Risk: {riskComponents.atr_risk || 'N/A'}/10</div>
          <div>Drawdown: {riskComponents.drawdown_risk || 'N/A'}/10</div>
          <div>Gap Risk: {riskComponents.gap_risk || 'N/A'}/10</div>
          <div>Volume: {riskComponents.volume_consistency || 'N/A'}/10</div>
          <div>Trend: {riskComponents.trend_stability || 'N/A'}/10</div>
        </div>
      </div>
    </div>
  );
};

function getRiskConfig(score) {
  if (score <= 2.0) {
    return { 
      level: 'Very Low', 
      color: 'from-emerald-500 to-green-400',
      bgColor: 'bg-emerald-500/10',
      textColor: 'text-emerald-400',
      borderColor: 'border-emerald-500/30'
    };
  } else if (score <= 3.5) {
    return { 
      level: 'Low', 
      color: 'from-green-500 to-lime-400',
      bgColor: 'bg-green-500/10',
      textColor: 'text-green-400',
      borderColor: 'border-green-500/30'
    };
  } else if (score <= 5.0) {
    return { 
      level: 'Medium', 
      color: 'from-yellow-500 to-amber-400',
      bgColor: 'bg-yellow-500/10',
      textColor: 'text-yellow-400',
      borderColor: 'border-yellow-500/30'
    };
  } else if (score <= 7.0) {
    return { 
      level: 'High', 
      color: 'from-orange-500 to-red-400',
      bgColor: 'bg-orange-500/10',
      textColor: 'text-orange-400',
      borderColor: 'border-orange-500/30'
    };
  } else if (score <= 8.5) {
    return { 
      level: 'Very High', 
      color: 'from-red-500 to-rose-400',
      bgColor: 'bg-red-500/10',
      textColor: 'text-red-400',
      borderColor: 'border-red-500/30'
    };
  } else {
    return { 
      level: 'Extreme', 
      color: 'from-red-600 to-pink-500',
      bgColor: 'bg-red-600/10',
      textColor: 'text-red-400',
      borderColor: 'border-red-600/30'
    };
  }
}

export default RiskMeter; 