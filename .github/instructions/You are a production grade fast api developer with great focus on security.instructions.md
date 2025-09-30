---
applyTo: '**'
---
Provide project context and coding guidelines that AI should follow when generating code, answering questions, or reviewing changes.

1. **Project Context**:
   - This project is a FastAPI application focused on providing a secure and efficient API for managing meeting notes and related tasks.
   - The application will handle sensitive user data, so security best practices must be followed.

2. **Coding Guidelines**:
   - Use type hints and Pydantic models for request and response bodies to ensure data validation and serialization.
   - Implement authentication and authorization using OAuth2 and JWT tokens.
   - Sanitize and validate all user inputs to prevent SQL injection and other attacks.
   - Use HTTPS for all communications to protect data in transit.
   - Write unit tests for all critical components to ensure reliability and facilitate future changes.
   - Document all API endpoints using OpenAPI standards.