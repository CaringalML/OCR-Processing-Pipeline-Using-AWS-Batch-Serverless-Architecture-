import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

const StatsCard = ({ label, value, change, trend = "neutral", className = "" }) => {
  const isPositive = change && change.startsWith('+');
  
  // Color scheme based on label and trend
  const getCardColors = (label, trend) => {
    if (label === "Failed") {
      return trend === "up" ? "border-red-200 bg-red-50" : "border-green-200 bg-green-50";
    }
    
    switch (trend) {
      case "up": return "border-green-200 bg-green-50";
      case "down": return label === "Failed" ? "border-green-200 bg-green-50" : "border-red-200 bg-red-50";
      case "neutral": return "border-gray-200 bg-white";
      default: return "border-gray-200 bg-white";
    }
  };

  const getTrendIcon = (trend) => {
    switch (trend) {
      case "up": return <TrendingUp className="w-4 h-4" />;
      case "down": return <TrendingDown className="w-4 h-4" />;
      case "neutral": return <Minus className="w-4 h-4" />;
      default: return null;
    }
  };

  const getTrendColor = (label, trend) => {
    if (label === "Failed") {
      return trend === "up" ? "text-red-600" : "text-green-600";
    }
    
    switch (trend) {
      case "up": return "text-green-600";
      case "down": return "text-red-600";
      case "neutral": return "text-gray-600";
      default: return "text-gray-600";
    }
  };
  
  return (
    <div className={`rounded-lg p-6 shadow-sm border hover:shadow-md transition-all duration-200 ${getCardColors(label, trend)} ${className}`}>
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-700">{label}</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
        </div>
        <div className="flex flex-col items-end space-y-1">
          {change && (
            <div className={`text-sm font-medium ${getTrendColor(label, trend)} flex items-center space-x-1`}>
              {getTrendIcon(trend)}
              <span>{change}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default StatsCard;