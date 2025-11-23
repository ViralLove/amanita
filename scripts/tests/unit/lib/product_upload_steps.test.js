/**
 * Unit Tests: product_upload_steps.js
 *
 * Focus: registerProductsInContract – ensure businessId is forwarded to createProduct
 *        and events parsed correctly after ProductRegistry update.
 */

const { expect } = require('chai');
const sinon = require('sinon');
const Module = require('module');
const path = require('path');

describe('product_upload_steps.registerProductsInContract', () => {
  let originalRequire;
  let sleepStub;
  let productUploadSteps;
  let registerProductsInContract;
  const modulePath = path.resolve(__dirname, '../../../lib/product_upload_steps.js');

  beforeEach(() => {
    // Stub sleep to skip real delays
    sleepStub = sinon.stub().resolves();

    // Intercept require for ./upload_utils before loading module under test
    originalRequire = Module.prototype.require;
    Module.prototype.require = function (request) {
      if (request === './upload_utils') {
        return { sleep: sleepStub };
      }
      return originalRequire.apply(this, arguments);
    };

    delete require.cache[modulePath];
    productUploadSteps = require('../../../lib/product_upload_steps.js');
    registerProductsInContract = productUploadSteps.registerProductsInContract;
  });

  afterEach(() => {
    delete require.cache[modulePath];
    Module.prototype.require = originalRequire;
    sinon.restore();
  });

  it('should call createProduct with businessId and capture it from ProductCreated event', async () => {
    const createProductStub = sinon.stub().resolves({
      wait: sinon.stub().resolves({
        logs: [{}],
        transactionHash: '0xhash'
      })
    });

    const parseLogStub = sinon.stub().returns({
      name: 'ProductCreated',
      args: {
        productId: 1n,
        businessId: 'product_a'
      }
    });

    const context = {
      dryRun: false,
      productRegistry: {
        createProduct: createProductStub,
        interface: {
          parseLog: parseLogStub
        }
      }
    };

    const mappingData = {
      product_a: {
        product_cid: 'QmProductCID'
      }
    };

    const productData = {
      product_a: {
        components: [
          { component_business_id: 'amanita_muscaria' }
        ]
      }
    };

    const results = await registerProductsInContract(context, mappingData, productData);

    sinon.assert.calledWith(
      createProductStub,
      'product_a',
      ['amanita_muscaria'],
      'QmProductCID'
    );
    expect(results.product_a.contractProductId).to.equal('1');
    expect(results.product_a.contractBusinessId).to.equal('product_a');
    expect(results.product_a.success).to.be.true;
  });

  it('should record businessId in dry-run mode', async () => {
    const mathRandomStub = sinon.stub(Math, 'random').returns(0.123456); // deterministic

    const context = {
      dryRun: true
    };

    const mappingData = {
      product_b: {
        product_cid: 'QmCID'
      }
    };

    const productData = {
      product_b: {
        components: [
          { component_business_id: 'component1' }
        ]
      }
    };

    const results = await registerProductsInContract(context, mappingData, productData);

    expect(results.product_b.success).to.be.true;
    expect(results.product_b.contractBusinessId).to.equal('product_b');
    expect(results.product_b.contractProductId).to.be.a('number');

    mathRandomStub.restore();
  });
});

