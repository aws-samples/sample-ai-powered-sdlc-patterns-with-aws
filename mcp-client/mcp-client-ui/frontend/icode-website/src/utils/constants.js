// Application constants

export const APP_NAME = 'AI-Powered Software Development using AWS generative AI';

export const NAVIGATION_ITEMS = [
  {
    id: 'home',
    text: 'Home',
    href: '/'
  },
  {
    id: 'about',
    text: 'About',
    href: '/about'
  },
  {
    id: 'services',
    text: 'Services',
    href: '/services'
  },
  {
    id: 'contact',
    text: 'Contact',
    href: '/contact'
  }
];

export const BRAND_CONFIG = {
  name: APP_NAME,
  logo: null, // Can be updated with logo path later
  tagline: 'Innovation in Software Development with AWS Generative AI'
};

export const FOOTER_LINKS = [
  {
    id: 'privacy',
    text: 'Privacy Policy',
    href: '/privacy',
    external: false
  },
  {
    id: 'terms',
    text: 'Terms of Service',
    href: '/terms',
    external: false
  },
  {
    id: 'support',
    text: 'Support',
    href: '/support',
    external: false
  }
];

// Home page content configuration
export const HOME_PAGE_CONTENT = {
  hero: {
    title: 'AI-Powered Software Development using AWS generative AI',
    subtitle: 'Championing Development Excellence with AI-Powered Solutions',
    actions: [
      {
        id: 'learn-more',
        text: 'Learn More',
        variant: 'primary',
        href: '/about'
      }
    ]
  },
  features: [
    {
      id: 'enterprise-integration',
      title: 'Enterprise Tool Integration with AI Power',
      description: 'Supercharge your existing tools - whether Atlassian, or other enterprise solutions - with advanced Generative AI capabilities, making your familiar workflows even more powerful.',
      icon: '🔧'
    },
    {
      id: 'sdlc-acceleration',
      title: 'End-to-End SDLC Acceleration',
      description: 'Transform every phase of your development lifecycle with intelligent automation, from requirements gathering to deployment, delivering results faster while maintaining quality.',
      icon: '⚡'
    },
    {
      id: 'developer-experience',
      title: 'Seamless Developer Experience',
      description: 'Empower your teams with smart workflows that reduce complexity and eliminate repetitive tasks, letting developers focus on what matters most - building innovative solutions.',
      icon: '👨‍💻'
    }
  ],
  sections: [
    {
      id: 'about',
      title: 'About ICODE',
      content: 'We champion software development excellence by harnessing the power of Generative AI across your entire development lifecycle. Our platform seamlessly integrates with your enterprise tools and systems, empowering teams to accelerate innovation and transform ideas into solutions with unprecedented speed. We\'re obsessed with developer success, delivering intelligent automation and workflow optimization that helps teams build better software faster while maintaining operational excellence.',
      variant: 'default'
    }
  ]
};

// Theme and styling constants

// Theme and styling constants
export const THEME_CONFIG = {
  defaultMode: 'light',
  supportedModes: ['light', 'dark'],
  spacing: {
    xs: '4px',
    s: '8px',
    m: '16px',
    l: '24px',
    xl: '32px',
    xxl: '48px'
  }
};