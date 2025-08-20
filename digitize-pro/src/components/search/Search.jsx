import React, { useState } from 'react';
import { Search as SearchIcon, FileText } from 'lucide-react';
import useSearch from '../../hooks/useSearch';
import uploadService from '../../services/uploadService';

const Search = () => {
  const [query, setQuery] = useState('');
  const [searchOptions, setSearchOptions] = useState({
    fullText: true,
    metadataOnly: false,
    exactPhrase: false
  });
  const { searchResults, searching, searchError, quickSearch, clearSearch } = useSearch();

  const handleSearch = async (e) => {
    e.preventDefault();
    if (query.trim()) {
      await quickSearch(query);
    } else {
      clearSearch();
    }
  };

  const handleOptionChange = (option) => {
    setSearchOptions(prev => ({
      ...prev,
      [option]: !prev[option]
    }));
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Search Archive</h1>
        <button className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors">
          Advanced Search
        </button>
      </div>

      {/* Search Input */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="relative">
          <SearchIcon className="absolute left-3 top-3 w-5 h-5 text-gray-400" />
          <form onSubmit={handleSearch}>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search documents, metadata, or full text content..."
              className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
            />
          </form>
        </div>
        <div className="flex items-center space-x-4 mt-4">
          <label className="flex items-center">
            <input 
              type="checkbox" 
              checked={searchOptions.fullText}
              onChange={() => handleOptionChange('fullText')}
              className="w-4 h-4 text-green-600 border-gray-300 rounded focus:ring-green-500" 
            />
            <span className="ml-2 text-sm text-gray-600">Full text search</span>
          </label>
          <label className="flex items-center">
            <input 
              type="checkbox" 
              checked={searchOptions.metadataOnly}
              onChange={() => handleOptionChange('metadataOnly')}
              className="w-4 h-4 text-green-600 border-gray-300 rounded focus:ring-green-500" 
            />
            <span className="ml-2 text-sm text-gray-600">Metadata only</span>
          </label>
          <label className="flex items-center">
            <input 
              type="checkbox" 
              checked={searchOptions.exactPhrase}
              onChange={() => handleOptionChange('exactPhrase')}
              className="w-4 h-4 text-green-600 border-gray-300 rounded focus:ring-green-500" 
            />
            <span className="ml-2 text-sm text-gray-600">Exact phrase</span>
          </label>
        </div>
      </div>

      {/* Search Results */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Search Results</h2>
          <p className="text-sm text-gray-500 mt-1">
            {searching ? 'Searching...' : 
             searchResults.length > 0 ? `Found ${searchResults.length} result(s)` :
             query ? 'No results found' : 'Enter a search term to find documents'}
          </p>
          {searchError && (
            <p className="text-sm text-red-600 mt-1">Error: {searchError}</p>
          )}
        </div>
        <div className="divide-y divide-gray-200">
          {searching ? (
            <div className="p-8 text-center">
              <div className="spinner mx-auto"></div>
              <p className="text-sm text-gray-500 mt-2">Searching documents...</p>
            </div>
          ) : searchResults.length > 0 ? (
            searchResults.map((result, index) => (
              <div key={result.id || index} className="p-6 hover:bg-gray-50">
                <div className="flex items-start space-x-4">
                  <FileText className="w-6 h-6 text-gray-400 mt-1" />
                  <div className="flex-1">
                    <h3 className="font-medium text-gray-900">
                      {result.title || result.fileName || 'Untitled Document'}
                    </h3>
                    <p className="text-sm text-gray-600 mt-1">
                      {result.snippet || 'No description available'}
                    </p>
                    <div className="flex items-center space-x-4 mt-3 text-xs text-gray-500">
                      <span>Collection: {result.publication || 'Uncategorized'}</span>
                      <span>Size: {uploadService.formatFileSize(result.fileSize || 0)}</span>
                      {result.year && <span>Year: {result.year}</span>}
                      {result.matchField && <span>Match: {result.matchField}</span>}
                      {result.score && <span>Score: {Math.round(result.score)}%</span>}
                    </div>
                  </div>
                </div>
              </div>
            ))
          ) : query ? (
            <div className="p-8 text-center">
              <p className="text-gray-500">No documents found for "{query}"</p>
              <p className="text-sm text-gray-400 mt-1">Try different keywords or check spelling</p>
            </div>
          ) : (
            <div className="p-8 text-center">
              <p className="text-gray-500">Start typing to search documents</p>
              <p className="text-sm text-gray-400 mt-1">Search across document content, metadata, and filenames</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Search;