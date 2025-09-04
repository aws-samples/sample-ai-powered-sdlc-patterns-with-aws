# AI Assistant Frontend

React TypeScript application for the AI-powered software development assistant.

## Overview

This frontend provides a modern, responsive interface for interacting with the AI Assistant's Knowledge Base. Built with React, TypeScript, and AWS Amplify for authentication.

## Architecture

- **React 18** with TypeScript for type safety
- **React Router** for client-side routing with authentication guards
- **AWS Amplify** for Cognito authentication integration
- **CloudFront** distribution for global content delivery
- **S3** bucket for static asset hosting

## Key Features

- 🔐 **Secure Authentication** - AWS Cognito integration with role-based access
- 💬 **Real-time Chat** - Interactive chat interface with AI assistant
- 📄 **Document Management** - Upload and manage team documents
- 👨‍💼 **Admin Dashboard** - Administrative controls for knowledge base management
- 📱 **Responsive Design** - Works on desktop and tablet devices
- 🎨 **Modern UI** - Clean, accessible interface with dark/light theme support

## Project Structure

```
frontend/
├── public/                 # Static assets and HTML template
├── src/
│   ├── components/        # Reusable React components
│   ├── pages/            # Page-level components
│   ├── contexts/         # React context providers
│   ├── hooks/            # Custom React hooks
│   ├── services/         # API service layer
│   ├── types/            # TypeScript type definitions
│   ├── utils/            # Utility functions
│   ├── config/           # Configuration files
│   └── assets/           # Images, fonts, etc.
├── package.json          # Dependencies and scripts
├── tsconfig.json         # TypeScript configuration
└── README.md            # This file
```

## Configuration

The application is configured through environment variables and Terraform outputs:

### Environment Variables

```bash
REACT_APP_COGNITO_USER_POOL_ID=us-west-2_XXXXXXXXX
REACT_APP_COGNITO_USER_POOL_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
REACT_APP_COGNITO_USER_POOL_DOMAIN=ai-assistant-auth-xxxxxxxx
REACT_APP_API_GATEWAY_URL=https://xxxxxxxxxx.execute-api.us-west-2.amazonaws.com/dev
REACT_APP_CLOUDFRONT_URL=https://xxxxxxxxxx.cloudfront.net
REACT_APP_ENVIRONMENT=dev
REACT_APP_PROJECT_NAME=ai-assistant
```

### AWS Configuration

The application integrates with the following AWS services:

- **Amazon Cognito** - User authentication and authorization
- **API Gateway** - Backend API endpoints
- **Amazon Bedrock** - AI model integration (via backend)
- **CloudFront** - Content delivery network
- **S3** - Static asset hosting

## Development

### Prerequisites

- Node.js 16+ and npm
- AWS CLI configured with appropriate permissions
- Terraform (for infrastructure deployment)

### Local Development

```bash
# Install dependencies
npm install

# Start development server
npm start

# Run tests
npm test

# Build for production
npm run build
```

### Environment Setup

1. **Deploy Infrastructure**: Ensure the Terraform infrastructure is deployed first
2. **Configure Environment**: Set environment variables from Terraform outputs
3. **Install Dependencies**: Run `npm install`
4. **Start Development**: Run `npm start`

## Deployment

The frontend is automatically deployed to AWS infrastructure:

1. **Build Process**: React app is built for production
2. **S3 Upload**: Static assets are uploaded to S3 bucket
3. **CloudFront**: Distribution serves content globally
4. **Cache Invalidation**: CloudFront cache is invalidated on updates

### Deployment Commands

```bash
# Build the application
npm run build

# Deploy to S3 (via Terraform or AWS CLI)
aws s3 sync build/ s3://your-frontend-bucket --delete

# Invalidate CloudFront cache
aws cloudfront create-invalidation --distribution-id YOUR_DISTRIBUTION_ID --paths "/*"
```

## Authentication Flow

1. **Login**: User authenticates via AWS Cognito
2. **Token Management**: JWT tokens are managed by AWS Amplify
3. **API Calls**: Authenticated requests include Authorization header
4. **Role-Based Access**: UI components respect user roles (admin/user)
5. **Session Management**: Automatic token refresh and logout

## API Integration

The frontend communicates with the backend through:

- **REST API**: Standard HTTP requests via API Gateway
- **Authentication**: Bearer token authentication
- **Error Handling**: Comprehensive error handling and user feedback
- **Type Safety**: Full TypeScript interfaces for API responses

### API Endpoints

- `GET /api/documents` - List user documents
- `POST /api/documents` - Upload new document
- `DELETE /api/documents/{id}` - Delete document
- `POST /api/chat/ask` - Send chat message
- `GET /api/chat/history` - Get conversation history
- `GET /api/admin/*` - Admin-only endpoints

## Security Features

- **Content Security Policy** - Prevents XSS attacks
- **HTTPS Only** - All traffic encrypted in transit
- **CORS Configuration** - Proper cross-origin resource sharing
- **Input Validation** - Client-side and server-side validation
- **Role-Based Access** - UI components respect user permissions
- **Secure Headers** - Security headers via CloudFront

## Performance Optimizations

- **Code Splitting** - Lazy loading of route components
- **Bundle Optimization** - Webpack optimizations for smaller bundles
- **CDN Delivery** - CloudFront for fast global content delivery
- **Caching Strategy** - Appropriate cache headers for static assets
- **Image Optimization** - Optimized images and icons

## Accessibility

- **WCAG Compliance** - Follows Web Content Accessibility Guidelines
- **Keyboard Navigation** - Full keyboard accessibility
- **Screen Reader Support** - Proper ARIA labels and roles
- **Color Contrast** - Meets accessibility color contrast requirements
- **Focus Management** - Proper focus handling for interactive elements

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Troubleshooting

### Common Issues

1. **Authentication Errors**: Check Cognito configuration and callback URLs
2. **API Errors**: Verify API Gateway endpoints and CORS settings
3. **Build Failures**: Check Node.js version and dependency compatibility
4. **Deployment Issues**: Verify AWS permissions and S3 bucket access

### Debug Mode

Enable debug mode by setting `REACT_APP_ENVIRONMENT=dev` for additional logging.

## Contributing

1. Follow TypeScript best practices
2. Use provided ESLint and Prettier configurations
3. Write tests for new components and features
4. Follow the established component and file naming conventions
5. Update documentation for new features

## License

This project is part of the AI Assistant system and follows the same licensing terms.