# Contributing to AI-Powered Software Development Assistant

We welcome contributions to the AI-Powered Software Development Assistant project! This document provides guidelines for contributing to this AWS sample solution.

## Code of Conduct

This project adheres to the Amazon Open Source Code of Conduct. By participating, you are expected to uphold this code.

## How to Contribute

### Reporting Bugs

Before creating bug reports, please check the existing issues to avoid duplicates. When creating a bug report, include:

- **Clear title and description**
- **Steps to reproduce** the issue
- **Expected vs actual behavior**
- **Environment details** (OS, Node.js version, AWS region)
- **Screenshots or logs** if applicable

### Suggesting Enhancements

Enhancement suggestions are welcome! Please provide:

- **Clear title and description** of the enhancement
- **Use case and motivation** for the change
- **Detailed explanation** of how it would work
- **Alternative solutions** you've considered

### Pull Requests

1. **Fork the repository** and create your branch from `main`
2. **Follow the coding standards** outlined below
3. **Add tests** for any new functionality
4. **Update documentation** as needed
5. **Ensure all tests pass** before submitting
6. **Create a pull request** with a clear description

## Development Setup

### Prerequisites

- Node.js 18+ and npm
- AWS CLI configured with appropriate permissions
- AWS CDK v2 installed globally
- Git

### Local Development

```bash
# Clone your fork
git clone https://github.com/your-username/sample-ai-powered-sdlc-patterns-with-aws.git
cd sample-ai-powered-sdlc-patterns-with-aws/all-phases/ai-assistant

# Install dependencies
npm run install:all

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Deploy infrastructure (for testing)
npm run deploy:infrastructure

# Start development servers
npm run start:backend  # In one terminal
npm run start:frontend # In another terminal
```

## Coding Standards

### General Guidelines

- **Use TypeScript** for all new code
- **Follow existing code style** and patterns
- **Write clear, self-documenting code**
- **Add comments for complex logic**
- **Use meaningful variable and function names**

### Backend (Lambda Functions)

- Use **async/await** instead of callbacks
- Implement proper **error handling**
- Follow **single responsibility principle**
- Use **structured logging**
- Validate all **input parameters**

```typescript
// Good example
export const handler = async (event: APIGatewayProxyEvent): Promise<APIGatewayProxyResult> => {
  try {
    const user = getUserFromEvent(event);
    const result = await processUserRequest(user, event.body);
    
    return {
      statusCode: 200,
      body: JSON.stringify(result),
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
      }
    };
  } catch (error) {
    logger.error('Request processing failed', { error, requestId: event.requestContext.requestId });
    return {
      statusCode: 500,
      body: JSON.stringify({ error: 'Internal server error' })
    };
  }
};
```

### Frontend (React)

- Use **functional components** with hooks
- Implement **proper error boundaries**
- Follow **React best practices**
- Use **TypeScript interfaces** for props
- Implement **accessibility features**

```typescript
// Good example
interface ChatMessageProps {
  message: Message;
  isCurrentUser: boolean;
  onRetry?: () => void;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ 
  message, 
  isCurrentUser, 
  onRetry 
}) => {
  return (
    <div 
      className={`message ${isCurrentUser ? 'user' : 'assistant'}`}
      role="article"
      aria-label={`Message from ${isCurrentUser ? 'you' : 'assistant'}`}
    >
      <p>{message.content}</p>
      {message.error && onRetry && (
        <button onClick={onRetry} aria-label="Retry sending message">
          Retry
        </button>
      )}
    </div>
  );
};
```

### Infrastructure (CDK)

- Use **TypeScript** for CDK code
- Follow **AWS best practices**
- Implement **least privilege** IAM policies
- Use **environment variables** for configuration
- Add **resource tagging**

```typescript
// Good example
export class CognitoStack extends Stack {
  constructor(scope: Construct, id: string, props: StackProps) {
    super(scope, id, props);

    const userPool = new UserPool(this, 'UserPool', {
      userPoolName: `ai-assistant-users-${props.environment}`,
      selfSignUpEnabled: true,
      autoVerify: { email: true },
      passwordPolicy: {
        minLength: 8,
        requireLowercase: true,
        requireUppercase: true,
        requireDigits: true,
      },
      removalPolicy: RemovalPolicy.DESTROY, // Only for development
    });

    Tags.of(userPool).add('Environment', props.environment);
    Tags.of(userPool).add('Project', 'ai-assistant');
  }
}
```

## Testing Guidelines

### Unit Tests

- **Test all business logic**
- **Mock external dependencies**
- **Use descriptive test names**
- **Follow AAA pattern** (Arrange, Act, Assert)

```typescript
describe('DocumentService', () => {
  describe('uploadDocument', () => {
    it('should upload document and return metadata when valid file provided', async () => {
      // Arrange
      const mockFile = { name: 'test.pdf', size: 1024, type: 'application/pdf' };
      const mockUser = { userId: 'user-123' };
      
      // Act
      const result = await documentService.uploadDocument(mockUser, mockFile);
      
      // Assert
      expect(result).toHaveProperty('documentId');
      expect(result.fileName).toBe('test.pdf');
      expect(result.status).toBe('processing');
    });
  });
});
```

### Integration Tests

- **Test service interactions**
- **Use test databases/resources**
- **Clean up after tests**
- **Test error scenarios**

### End-to-End Tests

- **Test complete user workflows**
- **Use realistic test data**
- **Test across different browsers**
- **Include accessibility testing**

## Security Guidelines

### General Security

- **Never commit secrets** or credentials
- **Use environment variables** for configuration
- **Implement input validation** everywhere
- **Follow least privilege principle**
- **Enable encryption** at rest and in transit

### Authentication & Authorization

- **Validate JWT tokens** properly
- **Implement proper session management**
- **Use HTTPS** for all communications
- **Implement rate limiting**

### Data Protection

- **Encrypt sensitive data**
- **Implement proper access controls**
- **Log security events**
- **Regular security updates**

## Documentation

### Code Documentation

- **Document public APIs**
- **Include usage examples**
- **Explain complex algorithms**
- **Keep documentation up-to-date**

### Architecture Documentation

- **Update architecture diagrams**
- **Document design decisions**
- **Include deployment guides**
- **Maintain troubleshooting guides**

## Commit Guidelines

### Commit Messages

Use conventional commit format:

```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Test changes
- `chore`: Build/tooling changes

Examples:
```
feat(auth): add Google OAuth integration
fix(documents): resolve file upload timeout issue
docs(readme): update deployment instructions
```

### Branch Naming

- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation updates
- `refactor/description` - Code refactoring

## Release Process

1. **Create release branch** from `main`
2. **Update version numbers** in package.json files
3. **Update CHANGELOG.md** with release notes
4. **Run full test suite**
5. **Create pull request** for review
6. **Merge to main** after approval
7. **Tag release** with version number

## Getting Help

- **Check existing issues** and documentation first
- **Join discussions** in GitHub Discussions
- **Ask questions** in issues with the `question` label
- **Contact maintainers** for security issues

## Recognition

Contributors will be recognized in:
- **CONTRIBUTORS.md** file
- **Release notes** for significant contributions
- **GitHub contributors** section

Thank you for contributing to the AI-Powered Software Development Assistant!
