export function isAuthorized(request, reply, relayAuthToken) {
    if (!relayAuthToken) {
        return true;
    }
    const header = request.headers.authorization;
    if (!header || !header.startsWith("Bearer ")) {
        reply.code(401).send({
            success: false,
            code: "UNAUTHORIZED",
            message: "Missing or invalid Authorization header",
        });
        return false;
    }
    const token = header.slice("Bearer ".length).trim();
    if (token !== relayAuthToken) {
        reply.code(401).send({
            success: false,
            code: "UNAUTHORIZED",
            message: "Invalid token",
        });
        return false;
    }
    return true;
}
