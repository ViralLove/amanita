/**
 * E2E: Action 41 - CSV → JSON Transform
 * 
 * Tests CSV parsing, validation, transformation to JSON format
 */

const { expect } = require('chai');
const E2EHarness = require('../../../helpers/E2EHarness');
const fs = require('fs');
const path = require('path');

describe('E2E: Action 41 - CSV Transform', function() {
  this.timeout(60000);

  let harness;

  before(async function() {
    harness = new E2EHarness();
    await harness.startHardhatNode();
    harness.loadTestEnv();
    await harness.resetNetwork();
  });

  after(async () => {
    await harness.stopHardhatNode();
    harness.restoreEnv();
  });

  describe('CSV Reading & Parsing', () => {
    it('должен читать стандартный CSV fixture', async () => {
      const csvPath = path.join(__dirname, '../../../fixtures/catalog/test_catalog.csv');
      const csvData = fs.readFileSync(csvPath, 'utf8');
      
      expect(csvData).to.include('product_id');
      expect(csvData).to.include('name');
      expect(csvData).to.include('description');
      
      const lines = csvData.trim().split('\n');
      expect(lines.length).to.be.greaterThan(1); // Header + at least 1 product
      
      console.log(`✓ CSV fixture valid: ${lines.length - 1} products`);
    });

    it('должен парсить CSV в объекты', async () => {
      const csvPath = path.join(__dirname, '../../../fixtures/catalog/test_catalog.csv');
      const csvData = fs.readFileSync(csvPath, 'utf8');
      
      const lines = csvData.trim().split('\n');
      const headers = lines[0].split(',');
      const products = [];
      
      for (let i = 1; i < lines.length; i++) {
        const values = lines[i].split(',');
        const product = {};
        headers.forEach((header, index) => {
          product[header] = values[index];
        });
        products.push(product);
      }
      
      expect(products).to.have.length.greaterThan(0);
      expect(products[0]).to.have.property('product_id');
      expect(products[0]).to.have.property('name');
      
      console.log(`✓ Parsed ${products.length} products from CSV`);
    });

    it('должен валидировать CSV schema', async () => {
      const csvPath = path.join(__dirname, '../../../fixtures/catalog/test_catalog.csv');
      const csvData = fs.readFileSync(csvPath, 'utf8');
      
      const lines = csvData.trim().split('\n');
      const headers = lines[0].split(',');
      
      // Required headers
      const requiredHeaders = ['product_id', 'name', 'description', 'price', 'category'];
      
      requiredHeaders.forEach(required => {
        expect(headers).to.include(required);
      });
      
      console.log('✓ CSV schema valid (all required headers present)');
    });
  });

  describe('CSV Transformation', () => {
    it('должен трансформировать CSV → JSON', async () => {
      const csvPath = path.join(__dirname, '../../../fixtures/catalog/test_catalog.csv');
      const csvData = fs.readFileSync(csvPath, 'utf8');
      
      const lines = csvData.trim().split('\n');
      const headers = lines[0].split(',');
      const products = [];
      
      for (let i = 1; i < lines.length; i++) {
        const values = lines[i].split(',');
        const product = {};
        headers.forEach((header, index) => {
          product[header] = values[index];
        });
        products.push(product);
      }
      
      const json = JSON.stringify(products, null, 2);
      
      expect(json).to.be.a('string');
      expect(JSON.parse(json)).to.be.an('array');
      
      console.log(`✓ Transformed CSV → JSON (${products.length} products)`);
    });

    it('должен валидировать types в transformed JSON', async () => {
      const csvPath = path.join(__dirname, '../../../fixtures/catalog/test_catalog.csv');
      const csvData = fs.readFileSync(csvPath, 'utf8');
      
      const lines = csvData.trim().split('\n');
      const headers = lines[0].split(',');
      const products = [];
      
      for (let i = 1; i < lines.length; i++) {
        const values = lines[i].split(',');
        const product = {
          product_id: values[0],
          name: values[1],
          description: values[2],
          price: parseFloat(values[3]), // Convert to number
          category: values[4]
        };
        products.push(product);
      }
      
      products.forEach(product => {
        expect(product.product_id).to.be.a('string');
        expect(product.name).to.be.a('string');
        expect(product.price).to.be.a('number');
      });
      
      console.log('✓ Type validation passed');
    });
  });

  describe('Edge Cases', () => {
    it('должен обрабатывать empty CSV', async () => {
      const csvPath = path.join(__dirname, '../../../fixtures/catalog/empty_catalog.csv');
      const csvData = fs.readFileSync(csvPath, 'utf8');
      
      const lines = csvData.trim().split('\n');
      expect(lines.length).to.equal(1); // Only header
      
      const headers = lines[0].split(',');
      expect(headers).to.include('product_id');
      
      console.log('✓ Empty CSV handled (header only)');
    });

    it('должен обрабатывать special characters (кириллица, emoji)', async () => {
      const csvPath = path.join(__dirname, '../../../fixtures/catalog/special_chars_catalog.csv');
      const csvData = fs.readFileSync(csvPath, 'utf8');
      
      expect(csvData).to.include('Мухомор'); // Cyrillic
      expect(csvData).to.include('🍄'); // Emoji
      
      const lines = csvData.trim().split('\n');
      expect(lines.length).to.be.greaterThan(1);
      
      console.log('✓ Special characters handled (кириллица + emoji)');
    });

    it('должен обрабатывать large catalog (10+ products)', async () => {
      const csvPath = path.join(__dirname, '../../../fixtures/catalog/large_catalog.csv');
      const csvData = fs.readFileSync(csvPath, 'utf8');
      
      const lines = csvData.trim().split('\n');
      const productCount = lines.length - 1; // Exclude header
      
      expect(productCount).to.be.greaterThanOrEqual(10);
      
      console.log(`✓ Large catalog handled: ${productCount} products`);
    });

    it('должен detect malformed CSV', async () => {
      const csvPath = path.join(__dirname, '../../../fixtures/catalog/malformed_catalog.csv');
      const csvData = fs.readFileSync(csvPath, 'utf8');
      
      const lines = csvData.trim().split('\n');
      const headers = lines[0].split(',');
      const expectedColumnCount = headers.length;
      
      let malformedCount = 0;
      
      for (let i = 1; i < lines.length; i++) {
        const values = lines[i].split(',');
        if (values.length !== expectedColumnCount) {
          malformedCount++;
        }
      }
      
      expect(malformedCount).to.be.greaterThan(0);
      
      console.log(`✓ Malformed CSV detected: ${malformedCount} malformed rows`);
    });
  });

  describe('Performance', () => {
    it('должен быстро обрабатывать CSV (< 1s)', async () => {
      const csvPath = path.join(__dirname, '../../../fixtures/catalog/test_catalog.csv');
      
      const timer = harness.measureExecutionTime('CSV Processing');
      
      const csvData = fs.readFileSync(csvPath, 'utf8');
      const lines = csvData.trim().split('\n');
      const headers = lines[0].split(',');
      const products = [];
      
      for (let i = 1; i < lines.length; i++) {
        const values = lines[i].split(',');
        const product = {};
        headers.forEach((header, index) => {
          product[header] = values[index];
        });
        products.push(product);
      }
      
      const json = JSON.stringify(products, null, 2);
      
      const duration = timer.end();
      expect(duration).to.be.lessThan(1000);
    });
  });
});

