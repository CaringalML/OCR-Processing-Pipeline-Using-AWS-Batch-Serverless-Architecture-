import React from 'react';

const StatsCard = ({ label, value, change, className = "" }) => {
  const isPositive = change && change.startsWith('+');
  
  return (
    <div className={`bg-white rounded-lg p-6 shadow-sm border border-gray-200 hover:shadow-md transition-shadow ${className}`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-600">{label}</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
        </div>
        {change && (
          <div className={`text-sm font-medium ${
            isPositive ? 'text-green-600' : 'text-red-600'
          }`}>
            {change}
          </div>
        )}
      </div>
    </div>
  );
};

export default StatsCard;