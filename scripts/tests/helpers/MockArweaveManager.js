/**
 * Mock Arweave Manager
 * 
 * Provides a mock implementation of ArweaveManager for testing.
 */

class MockArweaveManager {
  constructor() {
    this.uploads = [];
    this.initialized = false;
    this.mockBalance = '1.5';
  }

  /**
   * Initialize Arweave (mocked)
   * @returns {Object} - Mock initialization result
   */
  async initialize() {
    this.initialized = true;
    return {
      success: true,
      client: { mock: true },
      key: { mock: true },
      wallet: '0xMockArweaveWallet',
      balance: { address: '0xMockArweaveWallet', balance: this.mockBalance }
    };
  }

  /**
   * Load Arweave key (mocked)
   * @returns {Object} - Mock key
   */
  async loadArweaveKey() {
    return { mock: true, kty: 'RSA' };
  }

  /**
   * Check wallet balance (mocked)
   * @returns {Object} - Mock balance info
   */
  async checkWalletBalance() {
    return {
      address: '0xMockArweaveWallet',
      balance: this.mockBalance
    };
  }

  /**
   * Upload JSON to Arweave (mocked)
   * @param {Object} jsonData - Data to upload
   * @param {Array} tags - Transaction tags
   * @returns {string} - Mock CID
   */
  async uploadJSON(jsonData, tags = []) {
    const mockCID = `QmMock${Date.now()}${Math.random().toString(36).substring(7)}`;
    
    this.uploads.push({
      type: 'json',
      data: jsonData,
      tags,
      cid: mockCID,
      timestamp: new Date().toISOString()
    });

    return mockCID;
  }

  /**
   * Upload data to Arweave (mocked)
   * @param {string|Buffer} data - Data to upload
   * @param {Array} tags - Transaction tags
   * @returns {string} - Mock CID
   */
  async uploadData(data, tags = []) {
    const mockCID = `QmMock${Date.now()}${Math.random().toString(36).substring(7)}`;
    
    this.uploads.push({
      type: 'data',
      data,
      tags,
      cid: mockCID,
      timestamp: new Date().toISOString()
    });

    return mockCID;
  }

  /**
   * Upload file to Arweave (mocked)
   * @param {string} filePath - Path to file
   * @param {Array} tags - Transaction tags
   * @returns {string} - Mock CID
   */
  async uploadFile(filePath, tags = []) {
    const mockCID = `QmMock${Date.now()}${Math.random().toString(36).substring(7)}`;
    
    this.uploads.push({
      type: 'file',
      filePath,
      tags,
      cid: mockCID,
      timestamp: new Date().toISOString()
    });

    return mockCID;
  }

  /**
   * Test connection (mocked)
   * @returns {Object} - Mock connection test result
   */
  async testConnection() {
    return {
      success: true,
      gateway: 'https://arweave.net',
      networkInfo: { height: 123456 }
    };
  }

  /**
   * Get all uploads
   * @returns {Array} - Array of upload records
   */
  getUploads() {
    return this.uploads;
  }

  /**
   * Get uploads by type
   * @param {string} type - Upload type (json, data, file)
   * @returns {Array} - Filtered uploads
   */
  getUploadsByType(type) {
    return this.uploads.filter(upload => upload.type === type);
  }

  /**
   * Clear all uploads
   */
  clearUploads() {
    this.uploads = [];
  }

  /**
   * Reset mock
   */
  reset() {
    this.uploads = [];
    this.initialized = false;
  }
}

module.exports = MockArweaveManager;

