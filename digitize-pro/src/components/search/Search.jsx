import React, { useState, useEffect } from 'react';
import { Search as SearchIcon, FileText, ChevronDown, Download, Quote, Star, Clock, FileImage } from 'lucide-react';
import useSearch from '../../hooks/useSearch';
import useDebounce from '../../hooks/useDebounce';

const Search = () => {
  const [query, setQuery] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [advancedFilters, setAdvancedFilters] = useState({
    author: '',
    publication: '',
    yearFrom: '',
    yearTo: ''
  });
  const { searchResults, searching, searchError, quickSearch, advancedSearch, clearSearch } = useSearch();
  
  // Debounce search query
  const debouncedQuery = useDebounce(query, 500);

  // Auto-search when debounced query changes
  useEffect(() => {
    if (debouncedQuery.trim()) {
      performSearch();
    } else {
      clearSearch();
    }
  }, [debouncedQuery]);

  const performSearch = async () => {
    try {
      if (showAdvanced) {
        await advancedSearch({
          query: debouncedQuery.trim(),
          author: advancedFilters.author,
          publication: advancedFilters.publication,
          yearFrom: advancedFilters.yearFrom,
          yearTo: advancedFilters.yearTo,
          sortBy: 'relevance',
          enableFuzzy: true,
          fuzzyThreshold: 70
        });
      } else {
        await quickSearch(debouncedQuery);
      }
    } catch (error) {
      console.error('Search failed:', error);
    }
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
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="text-green-600 hover:text-green-700 hover:bg-green-50 px-3 py-1 rounded-md text-sm flex items-center transition-colors"
            >
              Advanced search
              <ChevronDown className={`w-4 h-4 ml-1 transform transition-transform ${showAdvanced ? 'rotate-180' : ''}`} />
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

          {/* Advanced Search Panel */}
          {showAdvanced && (
            <div className="mt-4 p-5 bg-green-50 rounded-lg border border-green-200">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-green-800 mb-1">
                    All these words
                  </label>
                  <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    className="w-full px-3 py-2 border border-green-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-green-800 mb-1">
                    Author
                  </label>
                  <input
                    type="text"
                    value={advancedFilters.author}
                    onChange={(e) => setAdvancedFilters(prev => ({ ...prev, author: e.target.value }))}
                    placeholder="e.g., John Doe"
                    className="w-full px-3 py-2 border border-green-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-green-800 mb-1">
                    Publication
                  </label>
                  <input
                    type="text"
                    value={advancedFilters.publication}
                    onChange={(e) => setAdvancedFilters(prev => ({ ...prev, publication: e.target.value }))}
                    placeholder="e.g., Nature"
                    className="w-full px-3 py-2 border border-green-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-green-800 mb-1">
                    Date range
                  </label>
                  <div className="flex gap-2 items-center">
                    <input
                      type="text"
                      value={advancedFilters.yearFrom}
                      onChange={(e) => setAdvancedFilters(prev => ({ ...prev, yearFrom: e.target.value }))}
                      placeholder="From"
                      className="w-24 px-3 py-2 border border-green-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
                    />
                    <span className="text-gray-500">to</span>
                    <input
                      type="text"
                      value={advancedFilters.yearTo}
                      onChange={(e) => setAdvancedFilters(prev => ({ ...prev, yearTo: e.target.value }))}
                      placeholder="To"
                      className="w-24 px-3 py-2 border border-green-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
                    />
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Search Status Bar */}
          {(searchResults.length > 0 || searching) && (
            <div className="mt-4 flex items-center justify-between text-sm">
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
                      {result.year && (
                        <>
                          <span>{result.year}</span>
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
                  {result.fileUrl && (
                    <a
                      href={result.fileUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center text-green-600 hover:text-green-700 hover:bg-green-50 px-2 py-1 rounded transition-colors"
                    >
                      <Download className="w-4 h-4 mr-1" />
                      Download
                    </a>
                  )}
                  <button className="inline-flex items-center text-gray-500 hover:text-green-600 hover:bg-green-50 px-2 py-1 rounded transition-colors">
                    <Quote className="w-4 h-4 mr-1" />
                    Cite
                  </button>
                  <button className="inline-flex items-center text-gray-500 hover:text-green-600 hover:bg-green-50 px-2 py-1 rounded transition-colors">
                    <Star className="w-4 h-4 mr-1" />
                    Save
                  </button>
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
            <div className="mt-6 flex justify-center gap-4 text-sm">
              <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full">
                Auto-search enabled
              </span>
              <span className="px-3 py-1 bg-gray-100 text-gray-600 rounded-full">
                Fuzzy matching
              </span>
              <span className="px-3 py-1 bg-gray-100 text-gray-600 rounded-full">
                Full-text search
              </span>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
};

export default Search;