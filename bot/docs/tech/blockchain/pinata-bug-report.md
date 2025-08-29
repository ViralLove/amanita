Subject: Critical API Bug - NO_SCOPES_FOUND Error Despite Correct Permissions

Dear Pinata Support Team,

I am writing to report a critical bug in your API that is completely blocking our ability to upload files to IPFS. This issue affects our production system and requires immediate attention.

CRITICAL ISSUE DESCRIPTION

Problem Summary:
API keys are returning 403 Forbidden - NO_SCOPES_FOUND errors for all file upload operations, despite having correct permissions set in the Pinata Dashboard interface.

Impact:
- Complete blockage of all file upload operations
- Production system down - unable to upload product metadata to IPFS
- Affects multiple API keys - both existing and newly created

TECHNICAL DETAILS

Affected API Key:
- Key: 3ff02db3c80d555fae9e
- Name: Amanita
- Status: Active
- Created: Recently (fresh key for testing)

Dashboard Permissions (Screenshot Attached):
- Files: Write (enabled)
- Groups: Write (enabled)
- Gateways: None
- Analytics: None

API Behavior Analysis:

Working Operations:
GET https://api.pinata.cloud/data/testAuthentication
Headers: pinata_api_key: 3ff02db3c80d555fae9e, pinata_secret_api_key: [REDACTED]
Response: 200 OK
Body: {"message":"Congratulations! You are communicating with the Pinata API!"}

Failing Operations:
POST https://api.pinata.cloud/pinning/pinJSONToIPFS
Headers: pinata_api_key: 3ff02db3c80d555fae9e, pinata_secret_api_key: [REDACTED], Content-Type: application/json
Body: {"pinataContent": {"test": "data"}, "pinataMetadata": {"name": "test.json"}}
Response: 403 Forbidden
Body: {"error": {"reason": "NO_SCOPES_FOUND", "details": "This key does not have the required scopes associated with it"}}

POST https://api.pinata.cloud/pinning/pinFileToIPFS
Headers: pinata_api_key: 3ff02db3c80d555fae9e, pinata_secret_api_key: [REDACTED]
Files: {"file": "[binary data]"}
Response: 403 Forbidden
Body: {"error": {"reason": "NO_SCOPES_FOUND", "details": "This key does not have the required scopes associated with it"}}

GET https://api.pinata.cloud/data/pinList
Headers: pinata_api_key: 3ff02db3c80d555fae9e, pinata_secret_api_key: [REDACTED]
Response: 403 Forbidden
Body: {"error": {"reason": "NO_SCOPES_FOUND", "details": "This key does not have the required scopes associated with it"}}

EVIDENCE

Screenshot Evidence:
I have attached a screenshot showing the API key permissions in the Pinata Dashboard. The screenshot clearly shows:
- Key name: "Amanita"
- Files permission: Write (enabled)
- Groups permission: Write (enabled)
- Key status: Active

Previous Working State:
This API integration was working perfectly before. We have been using Pinata successfully for months to upload product metadata to IPFS. The issue appeared suddenly without any changes on our side.

Fresh Key Creation:
I created a completely new API key with the same permissions to rule out any corruption of the existing key. The new key exhibits the exact same behavior:
- Authentication works
- All upload operations fail with NO_SCOPES_FOUND

TROUBLESHOOTING STEPS TAKEN

What We've Tried:
1. Verified API key validity - Authentication endpoint works
2. Confirmed permissions - Dashboard shows correct settings
3. Created fresh API key - Same issue persists
4. Tested with cURL - Same results as Python
5. Tested different data formats - JSON, files, metadata
6. Tested JWT authentication - Same NO_SCOPES_FOUND error
7. Verified network connectivity - No proxy, stable connection
8. Checked rate limits - Well within limits (169/180 remaining)

What We've Ruled Out:
- Client-side code issues (tested with cURL)
- Network/proxy issues (direct connection)
- Rate limiting (well within limits)
- Data format issues (tested multiple formats)
- Key corruption (fresh key has same issue)

URGENCY

Business Impact:
- Production system down - Cannot upload product metadata
- Customer-facing impact - Product catalog updates blocked
- Development blocked - Cannot test new features
- Revenue impact - E-commerce functionality affected

Priority Level:
CRITICAL - Complete service outage

EXPECTED BEHAVIOR

Based on the permissions shown in the dashboard, we expect:
1. Authentication: 200 OK (working)
2. JSON Upload: 200 OK with CID (should work)
3. File Upload: 200 OK with CID (should work)
4. File List: 200 OK with data (should work)

CONTACT INFORMATION

- Email: zeya.metsapuu@gmail.com
- Workspace: Zeya_metsapuu@gmail_com
- Affected API Key: 3ff02db3c80d555fae9e
- Application: E-commerce product catalog system
- Previous Status: Working for months

ADDITIONAL INFORMATION

System Context:
- Application: WooCommerce plugin for decentralized commerce
- Use Case: Uploading product metadata to IPFS
- Scale: Production system with active customers
- Previous Reliability: Excellent (months of stable operation)

Technical Context:
- Integration Method: Direct API calls
- Error Rate: 100% failure rate for upload operations
- Reproducibility: 100% reproducible
- Affected Endpoints: All file upload and listing endpoints

ATTACHMENTS

1. Screenshot: Pinata Dashboard showing API key permissions
2. Test Results: Complete API response logs
3. cURL Commands: Reproducible test cases

Thank you for your urgent attention to this critical issue.

Best regards,
Evgeniya Slinko
CTO, Amanita Project
