import React, { useState, useRef, useEffect } from 'react';
import { Calendar, ChevronLeft, ChevronRight } from 'lucide-react';

const ModernDatePicker = ({ value, onChange, placeholder = "Select date", className = "" }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [currentMonth, setCurrentMonth] = useState(new Date().getMonth());
  const [currentYear, setCurrentYear] = useState(new Date().getFullYear());
  const [selectedDate, setSelectedDate] = useState(null);
  const [isEditingYear, setIsEditingYear] = useState(false);
  const [yearInput, setYearInput] = useState('');
  const [isTypingInInput, setIsTypingInInput] = useState(false);
  const [inputValue, setInputValue] = useState('');
  const containerRef = useRef(null);
  const yearInputRef = useRef(null);
  const mainInputRef = useRef(null);
  
  const months = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
  ];
  
  const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  
  // Initialize selected date from value prop
  useEffect(() => {
    if (value) {
      setInputValue(value);
      const date = parseDate(value);
      if (date) {
        setSelectedDate(date);
        setCurrentMonth(date.getMonth());
        setCurrentYear(date.getFullYear());
      }
    }
  }, [value]);
  
  // Close calendar when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);
  
  // Parse various date formats
  const parseDate = (dateStr) => {
    if (!dateStr) return null;
    
    // Try DD/MM/YYYY format
    const ddmmyyyy = dateStr.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
    if (ddmmyyyy) {
      return new Date(parseInt(ddmmyyyy[3]), parseInt(ddmmyyyy[2]) - 1, parseInt(ddmmyyyy[1]));
    }
    
    // Try MM/DD/YYYY format
    const mmddyyyy = dateStr.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
    if (mmddyyyy) {
      return new Date(parseInt(mmddyyyy[3]), parseInt(mmddyyyy[1]) - 1, parseInt(mmddyyyy[2]));
    }
    
    // Try YYYY-MM-DD format
    const yyyymmdd = dateStr.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/);
    if (yyyymmdd) {
      return new Date(parseInt(yyyymmdd[1]), parseInt(yyyymmdd[2]) - 1, parseInt(yyyymmdd[3]));
    }
    
    // Try just year YYYY
    const yyyy = dateStr.match(/^(\d{4})$/);
    if (yyyy) {
      return new Date(parseInt(yyyy[1]), 0, 1); // January 1st of that year
    }
    
    return null;
  };
  
  // Format date as DD/MM/YYYY
  const formatDate = (date) => {
    if (!date) return '';
    const day = date.getDate().toString().padStart(2, '0');
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    const year = date.getFullYear();
    return `${day}/${month}/${year}`;
  };
  
  // Get calendar days for current month
  const getCalendarDays = () => {
    const firstDay = new Date(currentYear, currentMonth, 1);
    const lastDay = new Date(currentYear, currentMonth + 1, 0);
    const startDate = new Date(firstDay);
    startDate.setDate(startDate.getDate() - firstDay.getDay());
    
    const days = [];
    const currentDate = new Date(startDate);
    
    // Generate 6 weeks (42 days) to ensure full calendar display
    for (let i = 0; i < 42; i++) {
      days.push(new Date(currentDate));
      currentDate.setDate(currentDate.getDate() + 1);
    }
    
    return days;
  };
  
  const handleDateSelect = (date) => {
    setSelectedDate(date);
    const formattedDate = formatDate(date);
    onChange(formattedDate);
    setIsOpen(false);
  };
  
  const navigateMonth = (direction) => {
    if (direction === 'prev') {
      if (currentMonth === 0) {
        setCurrentMonth(11);
        setCurrentYear(currentYear - 1);
      } else {
        setCurrentMonth(currentMonth - 1);
      }
    } else {
      if (currentMonth === 11) {
        setCurrentMonth(0);
        setCurrentYear(currentYear + 1);
      } else {
        setCurrentMonth(currentMonth + 1);
      }
    }
  };
  
  const navigateYear = (direction) => {
    setCurrentYear(currentYear + (direction === 'next' ? 1 : -1));
  };
  
  const handleYearClick = () => {
    setIsEditingYear(true);
    setYearInput(currentYear.toString());
    setTimeout(() => {
      if (yearInputRef.current) {
        yearInputRef.current.focus();
        yearInputRef.current.select();
      }
    }, 10);
  };
  
  const handleYearInputChange = (e) => {
    const value = e.target.value.replace(/\D/g, ''); // Only allow digits
    if (value.length <= 4) {
      setYearInput(value);
    }
  };
  
  const handleYearInputSubmit = (e) => {
    if (e.key === 'Enter' || e.type === 'blur') {
      const year = parseInt(yearInput);
      if (year >= 1000 && year <= 3000) {
        setCurrentYear(year);
      }
      setIsEditingYear(false);
      setYearInput('');
    }
    if (e.key === 'Escape') {
      setIsEditingYear(false);
      setYearInput('');
    }
  };
  
  const handleMainInputChange = (e) => {
    const value = e.target.value;
    setInputValue(value);
    setIsTypingInInput(true);
    
    // Auto-parse and validate as user types
    if (value.trim()) {
      const date = parseDate(value.trim());
      if (date) {
        setSelectedDate(date);
        setCurrentMonth(date.getMonth());
        setCurrentYear(date.getFullYear());
      }
    }
  };
  
  const handleMainInputSubmit = (e) => {
    if (e.key === 'Enter') {
      const trimmedValue = inputValue.trim();
      
      if (trimmedValue) {
        // Check if it's just a 4-digit year
        if (/^\d{4}$/.test(trimmedValue)) {
          const year = parseInt(trimmedValue);
          if (year >= 1000 && year <= 3000) {
            onChange(trimmedValue); // Just pass the year as-is
            setIsOpen(false);
            setIsTypingInInput(false);
            return;
          }
        }
        
        // Try to parse as full date
        const date = parseDate(trimmedValue);
        if (date) {
          const formattedDate = formatDate(date);
          onChange(formattedDate);
          setIsOpen(false);
          setIsTypingInInput(false);
        } else {
          // Invalid date format - keep input open for correction
          setIsOpen(true);
        }
      } else {
        // Empty input - clear the value
        onChange('');
        setSelectedDate(null);
        setIsOpen(false);
        setIsTypingInInput(false);
      }
    }
  };
  
  const handleMainInputBlur = () => {
    // Small delay to allow calendar clicks to register
    setTimeout(() => {
      if (!isOpen) {
        setIsTypingInInput(false);
      }
    }, 150);
  };
  
  const handleMainInputFocus = () => {
    setIsTypingInInput(true);
  };
  
  const isToday = (date) => {
    const today = new Date();
    return date.toDateString() === today.toDateString();
  };
  
  const isSelected = (date) => {
    return selectedDate && date.toDateString() === selectedDate.toDateString();
  };
  
  const isCurrentMonth = (date) => {
    return date.getMonth() === currentMonth;
  };
  
  return (
    <div className={`relative ${className}`} ref={containerRef}>
      {/* Input Field */}
      <div className="relative">
        <input
          ref={mainInputRef}
          type="text"
          value={inputValue}
          onChange={handleMainInputChange}
          onKeyDown={handleMainInputSubmit}
          onFocus={handleMainInputFocus}
          onBlur={handleMainInputBlur}
          placeholder={placeholder}
          className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 bg-white hover:border-gray-400 transition-colors"
        />
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
        >
          <Calendar className="w-5 h-5" />
        </button>
        {inputValue && (
          <div className="absolute right-10 top-1/2 transform -translate-y-1/2 text-xs text-green-600">
            {/^\d{4}$/.test(inputValue.trim()) ? '(Year only)' : ''}
          </div>
        )}
      </div>
      
      {/* Calendar Dropdown */}
      {isOpen && (
        <div className="absolute top-full left-0 mt-2 bg-white border border-gray-200 rounded-lg shadow-lg z-50 w-[460px]">
          {/* Header */}
          <div className="p-5 border-b border-gray-200">
            {/* Year Navigation */}
            <div className="flex items-center justify-between mb-2">
              <button
                onClick={() => navigateYear('prev')}
                className="p-1 hover:bg-gray-100 rounded transition-colors"
                disabled={isEditingYear}
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              
              {isEditingYear ? (
                <input
                  ref={yearInputRef}
                  type="text"
                  value={yearInput}
                  onChange={handleYearInputChange}
                  onKeyDown={handleYearInputSubmit}
                  onBlur={handleYearInputSubmit}
                  className="font-semibold text-lg text-center bg-blue-50 border border-blue-300 rounded px-2 py-1 w-20 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Year"
                />
              ) : (
                <button
                  onClick={handleYearClick}
                  className="font-semibold text-lg hover:bg-gray-100 px-3 py-1 rounded transition-colors cursor-pointer"
                  title="Click to edit year"
                >
                  {currentYear}
                </button>
              )}
              
              <button
                onClick={() => navigateYear('next')}
                className="p-1 hover:bg-gray-100 rounded transition-colors"
                disabled={isEditingYear}
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
            
            {/* Month Navigation */}
            <div className="flex items-center justify-between">
              <button
                onClick={() => navigateMonth('prev')}
                className="p-1 hover:bg-gray-100 rounded transition-colors"
                disabled={isEditingYear}
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="font-medium">{months[currentMonth]}</span>
              <button
                onClick={() => navigateMonth('next')}
                className="p-1 hover:bg-gray-100 rounded transition-colors"
                disabled={isEditingYear}
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
          
          {/* Calendar Grid */}
          <div className="p-5">
            {/* Day Headers */}
            <div className="grid grid-cols-7 gap-2 mb-3">
              {days.map(day => (
                <div key={day} className="text-center text-sm font-medium text-gray-500 py-3">
                  {day}
                </div>
              ))}
            </div>
            
            {/* Calendar Days */}
            <div className="grid grid-cols-7 gap-2">
              {getCalendarDays().map((date, index) => (
                <button
                  key={index}
                  onClick={() => handleDateSelect(date)}
                  className={`
                    h-10 w-10 text-sm rounded-lg transition-colors relative font-medium
                    ${isCurrentMonth(date) 
                      ? 'text-gray-900 hover:bg-green-50' 
                      : 'text-gray-400 hover:bg-gray-50'
                    }
                    ${isSelected(date) 
                      ? 'bg-green-600 text-white hover:bg-green-700' 
                      : ''
                    }
                    ${isToday(date) && !isSelected(date) 
                      ? 'bg-green-100 text-green-800 font-semibold' 
                      : ''
                    }
                  `}
                >
                  {date.getDate()}
                </button>
              ))}
            </div>
          </div>
          
          {/* Footer with quick actions */}
          <div className="p-4 border-t border-gray-200">
            <div className="flex justify-between items-center mb-2">
              <button
                onClick={() => {
                  const today = new Date();
                  handleDateSelect(today);
                }}
                className="text-sm text-green-600 hover:text-green-700 font-medium"
              >
                Today
              </button>
              <button
                onClick={() => {
                  setSelectedDate(null);
                  setInputValue('');
                  onChange('');
                  setIsOpen(false);
                }}
                className="text-sm text-gray-500 hover:text-gray-700"
              >
                Clear
              </button>
            </div>
            <div className="text-xs text-gray-500 text-center">
              💡 Tip: Type "1925" for year only, or "05/08/1925" for full date
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ModernDatePicker;