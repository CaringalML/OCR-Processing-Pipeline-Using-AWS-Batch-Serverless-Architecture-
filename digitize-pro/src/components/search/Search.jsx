import React, { useState, useEffect, useCallback } from 'react';
import { Search as SearchIcon, FileText, Clock, Filter } from 'lucide-react';
import useSearch from '../../hooks/useSearch';
import useDebounce from '../../hooks/useDebounce';
import ModernDatePicker from '../common/ModernDatePicker';

const Search = () => {
  const [query, setQuery] = useState('');
  const [dateFilter, setDateFilter] = useState('');
  const [showDateFilter, setShowDateFilter] = useState(false);
  const { searchResults, searching, searchError, advancedSearch, clearSearch } = useSearch();
  
  // Debounce search query - longer delay to allow complete year typing
  const debouncedQuery = useDebounce(query, 800);

  // Auto-detect date patterns in search query
  const detectAndSetDateSearch = useCallback((searchQuery) => {
    
    // Check for 4-digit year patterns (1800-2030)
    const yearPattern = /\b(1[8-9]\d{2}|20[0-3]\d)\b/;
    const yearMatch = searchQuery.match(yearPattern);
    
    if (yearMatch) {
      const year = yearMatch[0];
      
      // Check if it's a pure year search (just "1925" or "year 1925")
      const pureYearPattern = /^(year\s+)?\d{4}$/i;
      
      if (pureYearPattern.test(searchQuery.trim())) {
        
        // Directly trigger advanced search in the background without opening the panel
        console.log('🎯 Year detected:', year, 'from query:', searchQuery);
        setTimeout(async () => {
          try {
            // Smart fuzzy for years: Try exact year search first
            const exactSearchParams = {
              query: '',
              author: '',
              publication: '',
              yearFrom: year,
              yearTo: year,
              sortBy: 'relevance',
              enableFuzzy: false,
              fuzzyThreshold: 70
            };
            console.log('🚀 Trying exact year search for:', year);
            const exactResults = await advancedSearch(exactSearchParams);
            console.log('✅ Exact year search results:', exactResults);

            // If no results, try SMART EXPANDED YEAR RANGE for typos
            // Adaptive range based on era (historical docs need wider range)
            if (exactResults.results.length === 0) {
              console.log('🔄 No exact year results, trying smart expanded year range...');
              const yearInt = parseInt(year);
              
              // Smart range calculation based on historical period
              let yearRange = 1; // Default ±1 year
              if (yearInt < 1900) yearRange = 2;      // Historical docs: ±2 years
              else if (yearInt < 1950) yearRange = 1; // Early 1900s: ±1 year
              else if (yearInt < 2000) yearRange = 1; // Mid 1900s: ±1 year
              else yearRange = 1;                     // Modern: ±1 year
              
              const expandedRangeParams = {
                query: '',
                author: '',
                publication: '',
                yearFrom: (yearInt - yearRange).toString(),
                yearTo: (yearInt + yearRange).toString(),
                sortBy: 'relevance',
                enableFuzzy: false, // Use exact search with smart range
                fuzzyThreshold: 85
              };
              
              const expandedResults = await advancedSearch(expandedRangeParams);
              console.log(`✅ Smart expanded range ${yearInt-yearRange}-${yearInt+yearRange} for ${year} (±${yearRange} years):`, expandedResults);
              
              // If still no results, try even wider range for very old documents
              if (expandedResults.results.length === 0 && yearInt < 1800) {
                console.log('🔄 Still no results, trying wider range for very historical documents...');
                const wideRangeParams = {
                  ...expandedRangeParams,
                  yearFrom: (yearInt - 5).toString(),
                  yearTo: (yearInt + 5).toString()
                };
                const wideResults = await advancedSearch(wideRangeParams);
                console.log(`✅ Wide historical range ${yearInt-5}-${yearInt+5} for very old documents:`, wideResults);
              }
            }
          } catch (error) {
            console.error('❌ Date search failed:', error);
          }
        }, 200);
        return true;
      }
      
      // Check for date range patterns like "1920-1930" or "1920 to 1930"
      const rangePatterns = [
        /\b(\d{4})\s*[-–—]\s*(\d{4})\b/,
        /\b(\d{4})\s+to\s+(\d{4})\b/i,
        /\bfrom\s+(\d{4})\s+to\s+(\d{4})\b/i
      ];
      
      for (let pattern of rangePatterns) {
        const rangeMatch = searchQuery.match(pattern);
        if (rangeMatch) {
          const startYear = rangeMatch[1];
          const endYear = rangeMatch[2];
          
          // Remove the date range from the search query
          const cleanedQuery = searchQuery.replace(pattern, '').trim();
          if (cleanedQuery !== searchQuery) {
            setQuery(cleanedQuery);
          }
          
          // Trigger search with the year range filters in background
          setTimeout(async () => {
            try {
              await advancedSearch({
                query: cleanedQuery,
                author: '',
                publication: '',
                yearFrom: startYear,
                yearTo: endYear,
                sortBy: 'relevance',
                enableFuzzy: false, // Disable fuzzy for year range searches
                fuzzyThreshold: 70
              });
            } catch (error) {
              console.error('Date range search failed:', error);
            }
          }, 100);
          return true;
        }
      }
    }
    
    return false; // No date pattern detected
  }, [advancedSearch, setQuery]);

  // Smart fuzzy search for regular queries
  const smartQuickSearch = useCallback(async (query) => {
    try {
      // Try exact search first (using advancedSearch with fuzzy disabled)
      console.log('🚀 Trying exact text search for:', query);
      const exactResults = await advancedSearch({
        query: query,
        author: '',
        publication: '',
        yearFrom: '',
        yearTo: '',
        sortBy: 'relevance',
        enableFuzzy: false,
        fuzzyThreshold: 75
      });
      
      console.log('✅ Exact search results:', exactResults);
      
      // Check if we have good results (high relevance scores)
      const hasGoodResults = exactResults.results.length > 0 && 
        exactResults.results.some(result => (result.score || 100) >= 90);
      
      // If no good results and less than 3 results, try fuzzy as fallback
      if (!hasGoodResults && exactResults.results.length < 3) {
        console.log('🔄 No good exact results, trying fuzzy fallback for:', query);
        await advancedSearch({
          query: query,
          author: '',
          publication: '',
          yearFrom: '',
          yearTo: '',
          sortBy: 'relevance',
          enableFuzzy: true,
          fuzzyThreshold: 75 // Higher threshold for better quality
        });
      }
    } catch (error) {
      console.error('Smart quick search failed:', error);
    }
  }, [advancedSearch]);

  const performSearch = useCallback(async () => {
    try {
      if (dateFilter) {
        // If date filter is set, use advanced search with date parameters
        const yearFromDate = extractYearFromDate(dateFilter);
        const searchParams = {
          query: debouncedQuery,
          author: '',
          publication: '',
          yearFrom: yearFromDate ? yearFromDate.toString() : '',
          yearTo: yearFromDate ? yearFromDate.toString() : '',
          sortBy: 'relevance',
          enableFuzzy: false, // Smart fuzzy: start with exact
          fuzzyThreshold: 75
        };

        // Smart fuzzy for date filter searches
        console.log('🚀 Trying exact search with date filter:', searchParams);
        const exactResults = await advancedSearch(searchParams);
        
        // Fallback to fuzzy if needed
        const hasGoodResults = exactResults.results.length > 0 && 
          exactResults.results.some(result => (result.score || 100) >= 90);
        
        if (!hasGoodResults && exactResults.results.length < 3) {
          console.log('🔄 Date filter search: trying fuzzy fallback...');
          await advancedSearch({...searchParams, enableFuzzy: true});
        }
      } else {
        // Smart fuzzy for regular searches
        await smartQuickSearch(debouncedQuery);
      }
    } catch (error) {
      console.error('Search failed:', error);
    }
  }, [dateFilter, debouncedQuery, advancedSearch, smartQuickSearch]);

  // Helper function to extract year from date string
  const extractYearFromDate = (dateString) => {
    if (!dateString) return null;
    
    // Pure year (like "1925")
    if (/^\d{4}$/.test(dateString.trim())) {
      return parseInt(dateString.trim());
    }
    
    // Date format (like "05/08/1925" or "08/05/1925")
    const dateMatch = dateString.match(/\d{1,2}[/.-]\d{1,2}[/.-](\d{4})/);
    if (dateMatch) {
      return parseInt(dateMatch[1]);
    }
    
    return null;
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    if (query.trim()) {
      performSearch();
    }
  };

  const formatAuthors = (authors) => {
    if (!authors || authors.length === 0) return null;
    const authorList = authors.filter(a => a).join(', ');
    if (authorList.length > 60) {
      return authorList.substring(0, 60) + '...';
    }
    return authorList;
  };

  // Auto-search when debounced query or date filter changes
  useEffect(() => {
    if (debouncedQuery.trim() || dateFilter) {
      const trimmedQuery = debouncedQuery.trim();
      
      // Skip search for very short numeric queries (1-3 digits, likely partial years)
      if (/^\d{1,3}$/.test(trimmedQuery)) {
        console.log('🚫 Skipping search for short numeric query:', trimmedQuery);
        return;
      }
      
      // Auto-detect date patterns in query (if no explicit date filter is set)
      const dateDetected = dateFilter ? false : detectAndSetDateSearch(trimmedQuery);
      console.log('🔍 Date detected:', dateDetected, 'for query:', trimmedQuery);
      // Only perform normal search if no date was detected in query
      if (!dateDetected) {
        console.log('📝 Performing regular search for:', trimmedQuery);
        performSearch();
      } else {
        console.log('🚫 Skipping regular search, year search will handle it');
      }
    } else {
      clearSearch();
    }
  }, [debouncedQuery, dateFilter, performSearch, clearSearch, detectAndSetDateSearch]);

  // Elephind-style snippet highlighting with context
  const highlightSnippet = (text, searchTerm) => {
    if (!text || !searchTerm) return text;
    
    const terms = searchTerm.toLowerCase().split(' ').filter(t => t.length > 2);
    const textLower = text.toLowerCase();
    
    // Find the best match position
    let bestPosition = -1;
    let maxMatches = 0;
    
    for (let i = 0; i < text.length - 100; i++) {
      const window = textLower.substring(i, i + 200);
      const matches = terms.filter(term => window.includes(term)).length;
      if (matches > maxMatches) {
        maxMatches = matches;
        bestPosition = i;
      }
    }
    
    // Extract context around the best match
    const start = Math.max(0, bestPosition - 50);
    const end = Math.min(text.length, bestPosition + 250);
    let snippet = text.substring(start, end);
    
    // Add ellipsis
    if (start > 0) snippet = '...' + snippet;
    if (end < text.length) snippet = snippet + '...';
    
    // Highlight matching terms with Elephind-style bold
    const regex = new RegExp(`(${terms.join('|')})`, 'gi');
    return snippet.replace(regex, '<mark class="bg-yellow-200 font-semibold px-0.5">$1</mark>');
  };

  const getFileTypeIcon = (fileType) => {
    if (fileType?.includes('pdf')) return '📄';
    if (fileType?.includes('image')) return '🖼️';
    return '📄';
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header with Green Theme */}
      <div className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-normal">
              <span className="text-green-700 font-semibold">Archive</span>
              <span className="text-gray-600 ml-2">Search</span>
            </h1>
            <button
              onClick={() => setShowDateFilter(!showDateFilter)}
              className={`flex items-center px-3 py-1 rounded-md text-sm transition-colors ${
                showDateFilter || dateFilter 
                  ? 'text-green-700 bg-green-50' 
                  : 'text-green-600 hover:text-green-700 hover:bg-green-50'
              }`}
            >
              <Filter className="w-4 h-4 mr-1" />
              Date Filter
              {dateFilter && <span className="ml-1 text-xs">•</span>}
            </button>
          </div>
        </div>
      </div>

      {/* Search Bar Section */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <form onSubmit={handleSearch}>
            <div className="flex gap-3">
              <div className="flex-1 relative">
                <SearchIcon className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search documents (auto-searches as you type)"
                  className="w-full pl-12 pr-4 py-3 text-base border-2 border-gray-300 rounded-lg hover:border-green-400 focus:outline-none focus:border-green-500 focus:ring-2 focus:ring-green-100 transition-colors"
                  autoFocus
                />
                {searching && (
                  <div className="absolute right-4 top-1/2 transform -translate-y-1/2">
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-green-600"></div>
                  </div>
                )}
              </div>
              <button
                type="submit"
                disabled={searching || !query.trim()}
                className="px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Search
              </button>
            </div>
          </form>

          {/* Date Filter Panel */}
          {showDateFilter && (
            <div className="mt-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
              <div className="flex items-center gap-4">
                <div className="flex-1">
                  <label className="block text-sm font-medium text-blue-800 mb-2">
                    Filter by Date
                  </label>
                  <ModernDatePicker
                    value={dateFilter}
                    onChange={setDateFilter}
                    placeholder="Select date or type year (e.g., 1925)"
                    className="w-full max-w-md"
                  />
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => setDateFilter('')}
                    className="px-3 py-2 text-sm bg-gray-100 text-gray-600 rounded-md hover:bg-gray-200 transition-colors"
                  >
                    Clear
                  </button>
                  <button
                    onClick={() => setShowDateFilter(false)}
                    className="px-3 py-2 text-sm bg-blue-100 text-blue-700 rounded-md hover:bg-blue-200 transition-colors"
                  >
                    Hide
                  </button>
                </div>
              </div>
              {dateFilter && (
                <div className="mt-3 text-sm text-blue-700">
                  <span className="font-medium">Active filter:</span> Documents from {dateFilter}
                </div>
              )}
            </div>
          )}

          {/* Search Status Bar */}
          {(searchResults.length > 0 || searching) && (
            <div className="mt-4 space-y-2">
              <div className="flex items-center justify-between text-sm">
                <div className="text-gray-600">
                  {searching ? (
                    <span className="flex items-center">
                      <Clock className="w-4 h-4 mr-1 animate-pulse" />
                      Searching...
                    </span>
                  ) : (
                    <span>
                      About <span className="font-semibold text-green-700">{searchResults.length}</span> results
                      {query && <span> for "<span className="font-semibold">{query}</span>"</span>}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-4">
                  <button className="text-green-600 hover:text-green-700 hover:underline">
                    Sort by relevance
                  </button>
                  <span className="text-gray-400">|</span>
                  <button className="text-green-600 hover:text-green-700 hover:underline">
                    Sort by date
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Search Results - Elephind Style */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        {searchError ? (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-700">Error: {searchError}</p>
          </div>
        ) : searchResults.length > 0 ? (
          <div className="space-y-6">
            {searchResults.map((result, index) => (
              <div 
                key={result.id || index} 
                className="bg-white rounded-lg shadow-sm hover:shadow-md transition-shadow p-5 border border-gray-200"
              >
                {/* Document Header */}
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    {/* Title */}
                    <h3 className="mb-2">
                      <a
                        href={`/read/${result.id}`}
                        className="text-lg font-medium text-green-700 hover:text-green-800 hover:underline"
                      >
                        {getFileTypeIcon(result.fileType)} {result.title || result.fileName || `Document ${index + 1}`}
                      </a>
                    </h3>
                    
                    {/* Metadata Line */}
                    <div className="flex flex-wrap items-center gap-2 text-sm text-gray-600 mb-3">
                      {formatAuthors(result.authors) && (
                        <>
                          <span className="font-medium text-gray-700">{formatAuthors(result.authors)}</span>
                          <span className="text-gray-400">•</span>
                        </>
                      )}
                      {result.publication && (
                        <>
                          <span className="italic">{result.publication}</span>
                          <span className="text-gray-400">•</span>
                        </>
                      )}
                      {result.date && (
                        <>
                          <span>{result.date}</span>
                          <span className="text-gray-400">•</span>
                        </>
                      )}
                      <span className="text-gray-500">{result.fileSize || '0B'}</span>
                      {result.uploadDate && (
                        <>
                          <span className="text-gray-400">•</span>
                          <span className="text-gray-500">
                            {new Date(result.uploadDate).toLocaleDateString()}
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                  
                  {/* Match Score Badge */}
                  {result.matchField && (
                    <div className="ml-4">
                      <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                        {result.matchField === 'text' ? 'Full Text' : result.matchField}
                        {result.score && result.score < 100 && (
                          <span className="ml-1">({Math.round(result.score)}%)</span>
                        )}
                      </span>
                    </div>
                  )}
                </div>

                {/* Elephind-style Text Snippet with Highlighting */}
                <div className="bg-gray-50 rounded-md p-4 mb-3 border-l-4 border-green-500">
                  <div 
                    className="text-sm text-gray-700 leading-relaxed font-serif"
                    dangerouslySetInnerHTML={{ 
                      __html: result.snippet 
                        ? highlightSnippet(result.snippet, query)
                        : highlightSnippet(result.ocrResults?.finalizedText || '', query)
                    }}
                  />
                </div>

                {/* Action Links */}
                <div className="flex items-center gap-4 text-sm">
                  <a
                    href={`/read/${result.id}`}
                    className="inline-flex items-center text-green-600 hover:text-green-700 hover:bg-green-50 px-2 py-1 rounded transition-colors"
                  >
                    <FileText className="w-4 h-4 mr-1" />
                    Read Document
                  </a>
                </div>
              </div>
            ))}
          </div>
        ) : query && !searching ? (
          <div className="bg-white rounded-lg shadow-sm p-8 text-center">
            <p className="text-gray-600 text-lg">No results found for "{query}"</p>
            <p className="text-gray-500 text-sm mt-2">Try different keywords or check your spelling</p>
          </div>
        ) : !query ? (
          <div className="bg-white rounded-lg shadow-sm p-12 text-center">
            <SearchIcon className="w-16 h-16 text-green-300 mx-auto mb-4" />
            <h2 className="text-xl font-medium text-gray-700 mb-2">
              Search Your Document Archive
            </h2>
            <p className="text-gray-500">
              Start typing to search across all finalized documents
            </p>
            <div className="mt-6 space-y-4">
              <div className="flex justify-center gap-3 text-sm flex-wrap">
                <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full">
                  ⚡ Smart Date Search
                </span>
                <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full">
                  📅 Modern Calendar
                </span>
                <span className="px-3 py-1 bg-purple-100 text-purple-700 rounded-full">
                  🎯 Auto-detection
                </span>
                <span className="px-3 py-1 bg-gray-100 text-gray-600 rounded-full">
                  🔍 Fuzzy matching
                </span>
                <span className="px-3 py-1 bg-orange-100 text-orange-700 rounded-full">
                  📄 Full-text search
                </span>
              </div>
              <div className="text-center text-sm text-gray-500">
                <p className="mb-2"><strong>Enhanced Search Tips:</strong></p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2 max-w-3xl mx-auto">
                  <p>🔍 <strong>Smart Date Search:</strong> Type "1925" for instant year search</p>
                  <p>📅 <strong>Date Filter:</strong> Use the Date Filter button for precise date selection</p>
                  <p>⚡ <strong>Quick Typing:</strong> Just type the year in search box (e.g., "1925")</p>
                  <p>🎯 <strong>Auto-Detection:</strong> Search automatically detects date patterns</p>
                </div>
                <div className="mt-3 text-xs text-gray-400">
                  <p><strong>Date Format Support:</strong> "1925", "05/08/1925", "08/05/1925", "year 1925" all work!</p>
                  <p>Searches both document publication dates and upload dates</p>
                </div>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
};

export default Search;