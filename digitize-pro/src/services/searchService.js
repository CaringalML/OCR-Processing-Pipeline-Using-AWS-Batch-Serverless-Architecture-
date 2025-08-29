import authService from './authService.js';

const API_BASE_URL = process.env.REACT_APP_API_GATEWAY_URL;

/**
 * Search Service - Handles document search operations with API Gateway
 */
class SearchService {
  /**
   * Get authorization headers for API calls
   * @returns {Promise<Object>} Headers with Authorization token
   */
  async getAuthHeaders() {
    try {
      const accessToken = await authService.getAccessToken();
      if (!accessToken) {
        throw new Error('No access token available');
      }
      
      return {
        'Authorization': `Bearer ${accessToken}`,
        'Accept': 'application/json',
      };
    } catch (error) {
      console.error('Error getting auth headers:', error);
      throw new Error('Authentication required');
    }
  }
  /**
   * Search documents with intelligent fuzzy matching
   * @param {Object} params - Search parameters
   * @param {string} params.q - Search query (required)
   * @param {string} params.author - Author name filter
   * @param {string} params.publication - Publication name filter
   * @param {string} params.as_ylo - Year range start
   * @param {string} params.as_yhi - Year range end
   * @param {string} params.scisbd - Sort by: "relevance" or "date"
   * @param {number} params.num - Number of results
   * @param {boolean} params.fuzzy - Enable fuzzy search
   * @param {number} params.fuzzyThreshold - Fuzzy match threshold (0-100)
   * @returns {Promise<Object>} Search results
   */
  async searchDocuments(params) {
    try {
      // Allow empty query if we have year filters for date-only searches
      if (!params.q && !params.as_ylo && !params.as_yhi) {
        throw new Error('Search query or date filters are required');
      }

      const queryParams = new URLSearchParams();
      if (params.q) queryParams.append('q', params.q);
      
      // Add optional parameters
      if (params.author) queryParams.append('author', params.author);
      if (params.publication) queryParams.append('publication', params.publication);
      if (params.as_ylo) queryParams.append('as_ylo', params.as_ylo);
      if (params.as_yhi) queryParams.append('as_yhi', params.as_yhi);
      if (params.scisbd) queryParams.append('scisbd', params.scisbd);
      if (params.num) queryParams.append('num', params.num);
      if (params.fuzzy !== undefined) queryParams.append('fuzzy', params.fuzzy);
      if (params.fuzzyThreshold) queryParams.append('fuzzyThreshold', params.fuzzyThreshold);

      const url = `${API_BASE_URL}/batch/search?${queryParams.toString()}`;
      
      // Debug: Log the actual URL being called
      console.log('🔍 Search API URL:', url);
      console.log('🔍 Search params:', params);
      
      const headers = await this.getAuthHeaders();
      
      const response = await fetch(url, {
        method: 'GET',
        headers,
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Search API error:', response.status, errorText);
        throw new Error(`Search failed: ${response.status} - ${response.statusText}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Search error:', error);
      throw error;
    }
  }

  /**
   * Quick search with default parameters
   * @param {string} query - Search query
   * @returns {Promise<Object>} Search results
   */
  async quickSearch(query) {
    return this.searchDocuments({
      q: query,
      num: 20,
      fuzzy: true,
      fuzzyThreshold: 70
    });
  }

  /**
   * Advanced search with all filters
   * @param {Object} filters - Advanced search filters
   * @returns {Promise<Object>} Search results
   */
  async advancedSearch(filters) {
    const params = {
      q: filters.query || '',
      author: filters.author || '',
      publication: filters.publication || '',
      as_ylo: filters.yearFrom || '',
      as_yhi: filters.yearTo || '',
      scisbd: filters.sortBy || 'relevance',
      num: filters.limit || 50,
      fuzzy: filters.enableFuzzy !== false, // Default to true
      fuzzyThreshold: filters.fuzzyThreshold || 70
    };

    return this.searchDocuments(params);
  }

  /**
   * Search by author
   * @param {string} authorName - Author name
   * @param {string} additionalQuery - Additional search terms
   * @returns {Promise<Object>} Search results
   */
  async searchByAuthor(authorName, additionalQuery = '') {
    return this.searchDocuments({
      q: additionalQuery || authorName,
      author: authorName,
      fuzzy: true,
      fuzzyThreshold: 75
    });
  }

  /**
   * Search by publication
   * @param {string} publicationName - Publication name
   * @param {string} additionalQuery - Additional search terms
   * @returns {Promise<Object>} Search results
   */
  async searchByPublication(publicationName, additionalQuery = '') {
    return this.searchDocuments({
      q: additionalQuery || publicationName,
      publication: publicationName,
      fuzzy: true,
      fuzzyThreshold: 75
    });
  }

  /**
   * Search within date range
   * @param {string} query - Search query
   * @param {string} startYear - Start year
   * @param {string} endYear - End year
   * @returns {Promise<Object>} Search results
   */
  async searchByDateRange(query, startYear, endYear) {
    return this.searchDocuments({
      q: query,
      as_ylo: startYear,
      as_yhi: endYear,
      scisbd: 'date',
      fuzzy: true
    });
  }

  /**
   * Get search suggestions (if implemented in backend)
   * @param {string} query - Partial search query
   * @returns {Promise<Array>} Search suggestions
   */
  async getSearchSuggestions(query) {
    try {
      const headers = await this.getAuthHeaders();
      
      const response = await fetch(`${API_BASE_URL}/search/suggestions?q=${encodeURIComponent(query)}`, {
        method: 'GET',
        headers,
      });

      if (!response.ok) {
        // If suggestions endpoint doesn't exist, return empty array
        return [];
      }

      const data = await response.json();
      return data.suggestions || [];
    } catch (error) {
      console.error('Error fetching suggestions:', error);
      return [];
    }
  }

  /**
   * Parse search results for display
   * @param {Object} searchData - Raw search response
   * @returns {Object} Parsed search results
   */
  parseSearchResults(searchData) {
    if (!searchData || !searchData.results) {
      return {
        results: [],
        totalResults: 0,
        searchInfo: {},
        facets: {}
      };
    }

    return {
      results: searchData.results.map(result => ({
        id: result.fileId,
        title: result.title || result.fileName || 'Untitled Document',
        fileName: result.fileName || '',
        authors: result.authors || [result.author] || [],
        publication: result.publication || '',
        year: result.year || result.date || result.publication_year || '',
        snippet: result.snippet || result.ocrResults?.finalizedText?.substring(0, 200) || '',
        fileUrl: result.fileUrl || result.cloudFrontUrl || '',
        fileSize: result.fileSize || '0B',
        fileType: result.fileType || result.contentType || '',
        score: result.fuzzyScore || result.matchScore || result.score || 100,
        matchField: result.matchField || '',
        metadata: result.metadata || {},
        ocrResults: result.ocrResults || {},
        uploadDate: result.uploadDate || result.uploadTimestamp || '',
        processingStatus: result.processingStatus || ''
      })),
      totalResults: searchData.totalResults || searchData.results.length,
      searchInfo: searchData.searchInfo || {},
      facets: searchData.facets || {}
    };
  }

  /**
   * Highlight search terms in text
   * @param {string} text - Text to highlight
   * @param {string} searchQuery - Search query
   * @returns {string} HTML with highlighted terms
   */
  highlightSearchTerms(text, searchQuery) {
    if (!text || !searchQuery) return text;

    const terms = searchQuery.split(' ').filter(term => term.length > 2);
    let highlightedText = text;

    terms.forEach(term => {
      const regex = new RegExp(`(${term})`, 'gi');
      highlightedText = highlightedText.replace(regex, '<mark class="bg-yellow-200">$1</mark>');
    });

    return highlightedText;
  }

  /**
   * Build search query from filters
   * @param {Object} filters - Search filters
   * @returns {string} Search query string
   */
  buildSearchQuery(filters) {
    const queryParts = [];

    if (filters.keywords) {
      queryParts.push(filters.keywords);
    }

    if (filters.title) {
      queryParts.push(`title:"${filters.title}"`);
    }

    if (filters.content) {
      queryParts.push(filters.content);
    }

    return queryParts.join(' ');
  }
}

// Export singleton instance
const searchService = new SearchService();
export default searchService;

// Also export the class for testing
export { SearchService };