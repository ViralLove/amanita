/**
 * Assertion Helpers
 * 
 * Custom assertion utilities for tests.
 */

const { expect } = require('chai');

const BUSINESS_ID_REGEX = /^[a-z0-9\-_]+$/i;
const CID_REGEX = /^Qm[1-9A-HJ-NP-Za-km-z]{44}$/;
const INVITE_CODE_REGEX = /^AMANITA-[A-Z0-9-]+$/;

async function expectRevertCustom(txPromise, errorName, contract) {
  try {
    await txPromise;
    expect.fail(`Ожидался custom error ${errorName}, но транзакция прошла успешно`);
  } catch (error) {
    if (error && error.errorName) {
      expect(error.errorName).to.equal(errorName);
      return;
    }

    if (error && error.customErrorName) {
      expect(error.customErrorName).to.equal(errorName);
      return;
    }

    const message = (error?.message || '').toLowerCase();
    if (contract && message.includes('return data:')) {
      const match = message.match(/return data:\s*(0x[0-9a-f]+)/);
      if (match) {
        try {
          const selector = contract.interface.getError(errorName).selector.toLowerCase();
          if (match[1].startsWith(selector)) {
            return;
          }
        } catch (selectorError) {
          console.warn(`⚠️ Ошибка при парсинге селектора ${errorName}: ${selectorError.message}`);
        }
      }
    }

    expect(message).to.include(
      errorName.toLowerCase(),
      `Ожидался custom error ${errorName}, получено: ${error?.message || error}`
    );
  }
}

async function expectRevertReason(txPromise, reasonSubstring) {
  try {
    await txPromise;
    expect.fail(`Ожидался revert с сообщением "${reasonSubstring}", но транзакция прошла успешно`);
  } catch (error) {
    const message = error?.message || '';
    expect(message).to.include(
      reasonSubstring,
      `Ожидался revert с "${reasonSubstring}", получено: ${message}`
    );
  }
}

async function expectNotReverted(txPromise, failureMessage = 'Транзакция не должна была ревертиться') {
  try {
    await txPromise;
  } catch (error) {
    expect.fail(`${failureMessage}: ${error?.message || error}`);
  }
}

async function expectEvent(txPromise, contract, eventName, assertFn) {
  const tx = await txPromise;
  const receipt = await tx.wait();

  const parsedEvent = receipt.logs
    .map((log) => {
      try {
        return contract.interface.parseLog(log);
      } catch {
        return null;
      }
    })
    .find((event) => event && event.name === eventName);

  expect(parsedEvent, `Событие ${eventName} не найдено`).to.exist;

  if (assertFn) {
    await assertFn(parsedEvent.args);
  }

  return parsedEvent;
}

async function assertBusinessIdMapping(productRegistry, businessId, expectedProductId) {
  const productId = await productRegistry.getProductIdByBusinessId(businessId);
  expect(Number(productId)).to.equal(
    Number(expectedProductId),
    `Ожидался productId ${expectedProductId} для businessId ${businessId}, получено ${productId}`
  );
}

async function assertBusinessIdCleared(productRegistry, businessId) {
  await expectRevertCustom(
    productRegistry.getProductIdByBusinessId(businessId),
    'BusinessIdUnknown',
    productRegistry
  );
}

async function assertSoulIdentitySetup({
  spiralEngine,
  soulIdentity,
  expectedSoulIdentityAddress,
  expectedSoulboundCore,
  expectedSoulMetadata,
  soulboundCoreContract
}) {
  expect(spiralEngine, 'SpiralEngine instance is required').to.exist;
  expect(soulIdentity, 'SoulIdentity instance is required').to.exist;

  expect(expectedSoulIdentityAddress, 'Expected soulIdentity address is required').to.be.a('string');
  expect(expectedSoulboundCore, 'Expected soulboundCore address is required').to.be.a('string');
  expect(expectedSoulMetadata, 'Expected soulMetadata address is required').to.be.a('string');

  const linkedSoulIdentity = await spiralEngine.soulIdentity();
  expect(linkedSoulIdentity.toLowerCase(), 'SpiralEngine → SoulIdentity link mismatch').to.equal(
    expectedSoulIdentityAddress.toLowerCase()
  );

  const actualSoulboundCore = await soulIdentity.soulboundCore();
  expect(actualSoulboundCore.toLowerCase(), 'SoulIdentity.soulboundCore mismatch').to.equal(
    expectedSoulboundCore.toLowerCase()
  );

  const actualSoulMetadata = await soulIdentity.soulMetadata();
  expect(actualSoulMetadata.toLowerCase(), 'SoulIdentity.soulMetadata mismatch').to.equal(
    expectedSoulMetadata.toLowerCase()
  );

  if (soulboundCoreContract) {
    const metadataFromCore = await soulboundCoreContract.getMetadataContract();
    expect(metadataFromCore.toLowerCase(), 'SoulboundCore metadata contract mismatch').to.equal(
      expectedSoulMetadata.toLowerCase()
    );
  }

  return {
    linkedSoulIdentity,
    actualSoulboundCore,
    actualSoulMetadata
  };
}

async function assertSellerState(spiralEngine, sellerAddress, expectations = {}) {
  expect(spiralEngine, 'SpiralEngine instance is required').to.exist;
  expect(sellerAddress, 'Seller address is required').to.be.a('string');

  const usedInvite = await spiralEngine.usedInviteByUser(sellerAddress);
  const activated = Number(usedInvite) > 0;

  const SELLER_ROLE = await spiralEngine.SELLER_ROLE();
  const sellerRole = await spiralEngine.hasRole(SELLER_ROLE, sellerAddress);

  const ACTIVATOR_ROLE = await spiralEngine.ACTIVATOR_ROLE();
  const activatorRole = await spiralEngine.hasRole(ACTIVATOR_ROLE, sellerAddress);

  const activator = await spiralEngine.userActivator(sellerAddress);

  const state = {
    usedInvite,
    activated,
    sellerRole,
    activatorRole,
    activator
  };

  if (expectations.activated !== undefined) {
    expect(state.activated, 'Seller activation mismatch').to.equal(expectations.activated);
  }
  if (expectations.sellerRole !== undefined) {
    expect(state.sellerRole, 'SELLER_ROLE mismatch').to.equal(expectations.sellerRole);
  }
  if (expectations.activatorRole !== undefined) {
    expect(state.activatorRole, 'ACTIVATOR_ROLE mismatch').to.equal(expectations.activatorRole);
  }
  if (expectations.activatorAddress !== undefined) {
    expect(state.activator.toLowerCase(), 'Activator address mismatch').to.equal(
      expectations.activatorAddress.toLowerCase()
    );
  }
  if (expectations.usedInvite !== undefined) {
    expect(Number(state.usedInvite), 'usedInvite mismatch').to.equal(Number(expectations.usedInvite));
  }

  return state;
}

const assertionHelpers = {
  INVITE_CODE_REGEX,

  /**
   * Assert valid Ethereum address
   * @param {string} address - Address to validate
   */
  assertValidAddress(address) {
    expect(address).to.match(/^0x[a-fA-F0-9]{40}$/, 'Invalid Ethereum address format');
  },

  /**
   * Assert valid IPFS CID
   * @param {string} cid - CID to validate
   */
  assertValidCID(cid) {
    expect(cid).to.match(/^Qm[a-zA-Z0-9]{44}$/, 'Invalid IPFS CID format');
  },

  /**
   * Assert valid Amanita invite code
   * @param {string} invite - Invite code to validate
   */
  assertInviteFormat(invite) {
    expect(invite, 'Invite code must not be empty').to.exist;
    expect(invite).to.match(INVITE_CODE_REGEX, 'Invalid invite code format (expected AMANITA-...)');
  },

  /**
   * Assert valid transaction hash
   * @param {string} txHash - Transaction hash to validate
   */
  assertValidTxHash(txHash) {
    expect(txHash).to.match(/^0x[a-fA-F0-9]{64}$/, 'Invalid transaction hash format');
  },

  /**
   * Assert object has required properties
   * @param {Object} obj - Object to check
   * @param {Array<string>} properties - Required property names
   */
  assertHasProperties(obj, properties) {
    properties.forEach(prop => {
      expect(obj).to.have.property(prop, `Missing required property: ${prop}`);
    });
  },

  /**
   * Assert array has minimum length
   * @param {Array} arr - Array to check
   * @param {number} minLength - Minimum length
   */
  assertMinLength(arr, minLength) {
    expect(arr).to.be.an('array');
    expect(arr.length).to.be.at.least(minLength, `Array length ${arr.length} is less than minimum ${minLength}`);
  },

  /**
   * Assert execution time is within limit
   * @param {Function} fn - Function to execute
   * @param {number} maxMs - Maximum execution time in milliseconds
   */
  async assertExecutionTime(fn, maxMs) {
    const startTime = Date.now();
    await fn();
    const duration = Date.now() - startTime;
    expect(duration).to.be.lessThan(maxMs, `Execution time ${duration}ms exceeded limit ${maxMs}ms`);
  },

  /**
   * Assert function throws specific error
   * @param {Function} fn - Function to execute
   * @param {string|RegExp} errorMatch - Expected error message or pattern
   */
  async assertThrowsError(fn, errorMatch) {
    try {
      await fn();
      throw new Error('Expected function to throw an error, but it did not');
    } catch (error) {
      if (typeof errorMatch === 'string') {
        expect(error.message).to.include(errorMatch);
      } else {
        expect(error.message).to.match(errorMatch);
      }
    }
  },

  /**
   * Assert array contains item matching predicate
   * @param {Array} arr - Array to search
   * @param {Function} predicate - Predicate function
   */
  assertArrayContains(arr, predicate) {
    expect(arr).to.be.an('array');
    const found = arr.some(predicate);
    expect(found).to.be.true;
  },

  /**
   * Assert two objects are deeply equal
   * @param {Object} actual - Actual object
   * @param {Object} expected - Expected object
   */
  assertDeepEqual(actual, expected) {
    expect(actual).to.deep.equal(expected);
  },

  /**
   * Assert file exists
   * @param {string} filePath - Path to file
   */
  assertFileExists(filePath) {
    const fs = require('fs');
    expect(fs.existsSync(filePath)).to.be.true;
  },

  /**
   * Assert JSON file has valid structure
   * @param {string} filePath - Path to JSON file
   * @param {Object} expectedStructure - Expected structure (keys)
   */
  assertJSONStructure(filePath, expectedStructure) {
    const fs = require('fs');
    expect(fs.existsSync(filePath)).to.be.true;
    
    const content = JSON.parse(fs.readFileSync(filePath, 'utf8'));
    Object.keys(expectedStructure).forEach(key => {
      expect(content).to.have.property(key);
    });
  },

  assertBusinessIdFormat(value, message = 'Invalid businessId format') {
    expect(value, message).to.be.a('string');
    expect(value, message).to.match(BUSINESS_ID_REGEX);
  },

  assertCidFormat(value, message = 'Invalid CID format') {
    expect(value, message).to.be.a('string');
    expect(value, message).to.match(CID_REGEX);
  },

  assertRegisteredProxy(registry, contractName, expectedProxy, expectedImplementation) {
    expect(registry).to.be.an('object');
    const entry = registry[contractName];
    expect(entry, `Contract ${contractName} not registered`).to.exist;
    if (expectedProxy) {
      expect(entry.proxy.toLowerCase()).to.equal(expectedProxy.toLowerCase());
    }
    if (expectedImplementation) {
      expect(entry.implementation.toLowerCase()).to.equal(expectedImplementation.toLowerCase());
    }
    return entry;
  },

  assertSoulIdentitySetup,
  assertSellerState,

  expectRevertCustom,
  expectRevertReason,
  expectNotReverted,
  expectEvent,
  assertBusinessIdMapping,
  assertBusinessIdCleared
};

module.exports = assertionHelpers;

