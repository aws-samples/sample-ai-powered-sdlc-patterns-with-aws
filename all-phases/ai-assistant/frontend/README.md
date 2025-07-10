# Frontend Application

This directory contains the React frontend application for the AI-Powered Software Development Assistant.

## Structure

```
frontend/
├── public/                # Static assets
├── src/
│   ├── components/        # React components
│   │   ├── auth/         # Authentication components
│   │   ├── chat/         # Chat interface components
│   │   ├── documents/    # Document management components
│   │   ├── layout/       # Layout components
│   │   └── shared/       # Shared/common components
│   ├── services/         # API and service integrations
│   │   ├── auth.service.ts      # Authentication service
│   │   ├── document.service.ts  # Document management
│   │   ├── query.service.ts     # AI query service
│   │   └── api.client.ts        # HTTP client
│   ├── hooks/            # Custom React hooks
│   ├── contexts/         # React contexts
│   ├── types/            # TypeScript type definitions
│   ├── utils/            # Utility functions
│   ├── styles/           # CSS and styling
│   ├── App.tsx           # Main application component
│   └── index.tsx         # Application entry point
├── package.json          # Dependencies
├── tsconfig.json         # TypeScript configuration
├── tailwind.config.js    # Tailwind CSS configuration
└── README.md             # This file
```

## Features

### Authentication
- Multi-provider login (Cognito, Google, Amazon)
- User profile management
- Secure session handling
- Role-based UI rendering

### Document Management
- Drag-and-drop file upload
- Document list and search
- File type validation
- Upload progress tracking
- Document metadata editing

### AI Chat Interface
- Real-time chat interface
- Message history
- Typing indicators
- Response streaming
- Source attribution

### Responsive Design
- Mobile-first approach
- Cross-browser compatibility
- Accessibility compliance (WCAG 2.1)
- Dark/light theme support

## Technology Stack

- **React 18** with TypeScript
- **AWS Amplify** for authentication
- **Tailwind CSS** for styling
- **React Query** for state management
- **React Router** for navigation
- **Socket.io** for real-time communication

## Development

```bash
# Install dependencies
npm install

# Start development server
npm start

# Build for production
npm run build

# Run tests
npm test

# Run linting
npm run lint
```

## Environment Variables

Create a `.env` file with:
```
REACT_APP_AWS_REGION=us-east-1
REACT_APP_USER_POOL_ID=your-user-pool-id
REACT_APP_USER_POOL_CLIENT_ID=your-client-id
REACT_APP_IDENTITY_POOL_ID=your-identity-pool-id
REACT_APP_API_ENDPOINT=your-api-endpoint
REACT_APP_COGNITO_DOMAIN=your-cognito-domain
```

## Components

### Authentication Components
- `LoginForm` - Email/password login
- `SignupForm` - User registration
- `FederatedLogin` - Social login buttons
- `ProfileManager` - User profile editing

### Chat Components
- `ChatInterface` - Main chat container
- `MessageList` - Message display
- `MessageInput` - Input field with send button
- `TypingIndicator` - Shows when AI is processing

### Document Components
- `DocumentUpload` - File upload interface
- `DocumentList` - Document management
- `DocumentViewer` - Document preview
- `DocumentSearch` - Search and filter

## State Management

Using React Query for:
- API state management
- Caching and synchronization
- Background updates
- Optimistic updates

## Styling

- **Tailwind CSS** for utility-first styling
- **CSS Modules** for component-specific styles
- **Responsive design** with mobile-first approach
- **Accessibility** features built-in

## Testing

```bash
# Unit tests
npm run test:unit

# Integration tests
npm run test:integration

# E2E tests
npm run test:e2e

# Coverage report
npm run test:coverage
```

## Deployment

The frontend is deployed as a static website:
- Build artifacts served from S3
- CloudFront distribution for global CDN
- Custom domain with SSL certificate
- Automatic deployment via CI/CD pipeline

## Performance

- Code splitting for optimal loading
- Lazy loading of components
- Image optimization
- Bundle size optimization
- Progressive Web App features
