import Arweave from "arweave";
export class ArweaveClient {
    arweave;
    jwk;
    constructor(config) {
        this.arweave = Arweave.init({
            protocol: config.arweaveProtocol,
            host: config.arweaveHost,
            port: config.arweavePort,
        });
        this.jwk = config.jwk;
    }
}
