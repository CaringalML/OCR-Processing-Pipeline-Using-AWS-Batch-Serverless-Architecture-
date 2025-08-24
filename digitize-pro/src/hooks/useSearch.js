import { useState, useCallback } from 'react';
import searchService from '../services/searchService';

/**
 * Custom hook for document search
 */
const useSearch = () => {
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState(null);
  const [searchInfo, setSearchInfo] = useState(null);
  const [lastQuery, setLastQuery] = useState('');

  /**
   * Perform a search
   */
  const search = useCallback(async (params) => {
    // Allow empty query if we have year filters for date-only searches
    if ((!params.q || params.q.trim() === '') && !params.as_ylo && !params.as_yhi) {
      setSearchResults([]);
      return { results: [] };
    }

    setSearching(true);
    setSearchError(null);
    setLastQuery(params.q);

    try {
      const data = await searchService.searchDocuments(params);
      const parsed = searchService.parseSearchResults(data);
      
      setSearchResults(parsed.results);
      setSearchInfo(parsed.searchInfo);
      
      return parsed;
    } catch (error) {
      setSearchError(error.message);
      console.error('Search error:', error);
      throw error;
    } finally {
      setSearching(false);
    }
  }, []);

  /**
   * Quick search with default parameters
   */
  const quickSearch = useCallback(async (query) => {
    return search({
      q: query,
      fuzzy: true,
      fuzzyThreshold: 70,
      num: 20
    });
  }, [search]);

  /**
   * Advanced search with all filters
   */
  const advancedSearch = useCallback(async (filters) => {
    return search({
      q: filters.query || '',
      author: filters.author || '',
      publication: filters.publication || '',
      as_ylo: filters.yearFrom || '',
      as_yhi: filters.yearTo || '',
      scisbd: filters.sortBy || 'relevance',
      num: filters.limit || 50,
      fuzzy: filters.enableFuzzy !== false,
      fuzzyThreshold: filters.fuzzyThreshold || 70
    });
  }, [search]);

  /**
   * Search by author
   */
  const searchByAuthor = useCallback(async (authorName, additionalQuery = '') => {
    return search({
      q: additionalQuery || authorName,
      author: authorName,
      fuzzy: true,
      fuzzyThreshold: 75
    });
  }, [search]);

  /**
   * Search by publication
   */
  const searchByPublication = useCallback(async (publicationName, additionalQuery = '') => {
    return search({
      q: additionalQuery || publicationName,
      publication: publicationName,
      fuzzy: true,
      fuzzyThreshold: 75
    });
  }, [search]);

  /**
   * Search within date range
   */
  const searchByDateRange = useCallback(async (query, startYear, endYear) => {
    return search({
      q: query,
      as_ylo: startYear,
      as_yhi: endYear,
      scisbd: 'date',
      fuzzy: true
    });
  }, [search]);

  /**
   * Clear search results
   */
  const clearSearch = useCallback(() => {
    setSearchResults([]);
    setSearchInfo(null);
    setLastQuery('');
    setSearchError(null);
  }, []);

  /**
   * Highlight search terms in text
   */
  const highlightTerms = useCallback((text, query = lastQuery) => {
    return searchService.highlightSearchTerms(text, query);
  }, [lastQuery]);

  return {
    // State
    searchResults,
    searching,
    searchError,
    searchInfo,
    lastQuery,
    
    // Methods
    search,
    quickSearch,
    advancedSearch,
    searchByAuthor,
    searchByPublication,
    searchByDateRange,
    clearSearch,
    highlightTerms
  };
};

export default useSearch;