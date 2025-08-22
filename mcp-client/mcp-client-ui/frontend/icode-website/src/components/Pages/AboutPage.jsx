import { Header, Box, SpaceBetween } from '@cloudscape-design/components';
import { getAboutPageContent } from '../../utils/contentLoader';
import SectionContainer from '../UI/SectionContainer';

const AboutPage = () => {
  const { title, content } = getAboutPageContent();
  
  return (
    <SectionContainer
      header={<Header variant="h1">{title}</Header>}
    >
      <SpaceBetween size="l">
        
        <Box variant="p">
          {content}
        </Box>
        
        <Box variant="p">
          Our platform helps developers, project managers, and business stakeholders 
          collaborate more effectively by providing AI-driven insights, automated workflows, 
          and comprehensive project management capabilities.
        </Box>
      </SpaceBetween>
    </SectionContainer>
  );
};

export default AboutPage;