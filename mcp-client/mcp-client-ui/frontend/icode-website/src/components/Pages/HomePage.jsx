import { Box, Grid, SpaceBetween } from '@cloudscape-design/components';
import HeroSection from '../UI/HeroSection';
import FeatureCard from '../UI/FeatureCard';
import ContentSection from '../UI/ContentSection';
import HowItWorksTable from '../UI/HowItWorksTable';
import MyProjectsTable from '../UI/MyProjectsTable';
import { getHomePageContent } from '../../utils/contentLoader';

const HomePage = () => {
  const { hero, features } = getHomePageContent();

  return (
    <Box>
      <SpaceBetween direction="vertical" size="xl">
        {/* Hero Section */}
        <HeroSection
          title={hero.title}
          subtitle={hero.subtitle}
          actions={hero.actions}
        />
        


        {/* My Projects Section */}
        <MyProjectsTable />

        {/* Features Section */}
        <ContentSection title="Why Choose Our Platform" variant="default">
          <Grid
            gridDefinition={[
              { colspan: { default: 12, xs: 4 } },
              { colspan: { default: 12, xs: 4 } },
              { colspan: { default: 12, xs: 4 } }
            ]}
          >
            {features.map((feature) => (
              <FeatureCard
                key={feature.id}
                title={feature.title}
                description={feature.description}
                icon={feature.icon}
              />
            ))}
          </Grid>
        </ContentSection>



        {/* How AI-Powered Software Development using AWS generative AI Works Table */}
        <HowItWorksTable />
      </SpaceBetween>
    </Box>
  );
};

export default HomePage;