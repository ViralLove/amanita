const assert = require('assert');

class MagicRegistryHelper {
  constructor() {
    this.registry = {};
  }

  register(contractName, proxyAddress, implementationAddress) {
    assert(contractName, 'contractName is required');
    if (!proxyAddress) {
      throw new Error(`Proxy address is required for ${contractName}`);
    }

    this.registry[contractName] = {
      proxy: proxyAddress,
      implementation: implementationAddress || null
    };
  }

  registerMany(entries) {
    if (!Array.isArray(entries)) {
      throw new Error('registerMany expects an array of [contractName, proxy, implementation] tuples');
    }

    entries.forEach(([contractName, proxy, implementation]) => {
      this.register(contractName, proxy, implementation);
    });
  }

  resolve(contractName) {
    const entry = this.registry[contractName];
    if (!entry) {
      throw new Error(`Contract ${contractName} is not registered in MagicRegistryHelper`);
    }
    return entry;
  }

  getProxy(contractName) {
    return this.resolve(contractName).proxy;
  }

  getImplementation(contractName) {
    return this.resolve(contractName).implementation;
  }

  assertRegistration(contractName, expectedProxy, expectedImplementation) {
    const entry = this.resolve(contractName);
    if (expectedProxy) {
      assert.strictEqual(entry.proxy.toLowerCase(), expectedProxy.toLowerCase(), `Proxy mismatch for ${contractName}`);
    }
    if (expectedImplementation) {
      assert.strictEqual(
        (entry.implementation || '').toLowerCase(),
        expectedImplementation.toLowerCase(),
        `Implementation mismatch for ${contractName}`
      );
    }
    return entry;
  }

  clear() {
    this.registry = {};
  }
}

module.exports = MagicRegistryHelper;
