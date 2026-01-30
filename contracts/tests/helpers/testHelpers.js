/**
 * Общие хелперы для тестов контрактов (UUPS, custom errors, события).
 * Используются в ActivityRegistry.UUPS.comprehensive и при необходимости в других тестах.
 */
const chai = require("chai");
const { expect } = chai;

async function expectRevertCustom(txPromise, errorName, contract) {
    try {
        await txPromise;
        expect.fail(`Ожидался custom error ${errorName}, но транзакция прошла успешно`);
    } catch (error) {
        if (error && error.errorName) {
            expect(error.errorName).to.equal(errorName);
            return;
        }
        const message = (error?.message || "").toLowerCase();
        if (contract && message.includes("return data:")) {
            const match = message.match(/return data:\s*(0x[0-9a-f]+)/);
            if (match) {
                const selector = contract.interface.getError(errorName).selector.toLowerCase();
                if (match[1].startsWith(selector)) {
                    return;
                }
            }
        }
        expect(message).to.include(errorName.toLowerCase(), `Ожидался custom error ${errorName}, получено: ${error?.message || error}`);
    }
}

async function expectRevertReason(txPromise, reasonSubstring) {
    try {
        await txPromise;
        expect.fail(`Ожидался revert с сообщением "${reasonSubstring}", но транзакция прошла успешно`);
    } catch (error) {
        const message = error?.message || "";
        expect(message).to.include(reasonSubstring, `Ожидался revert с "${reasonSubstring}", получено: ${message}`);
    }
}

async function expectNotReverted(txPromise, failureMessage = "Транзакция не должна была ревертиться") {
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
        .map(log => {
            try {
                return contract.interface.parseLog(log);
            } catch (_) {
                return null;
            }
        })
        .find(event => event && event.name === eventName);

    expect(parsedEvent, `Событие ${eventName} не найдено`).to.exist;

    if (assertFn) {
        await assertFn(parsedEvent.args);
    }

    return parsedEvent;
}

module.exports = {
    expectRevertCustom,
    expectRevertReason,
    expectNotReverted,
    expectEvent
};
