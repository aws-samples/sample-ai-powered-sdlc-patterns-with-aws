import {
  Header,
  SpaceBetween,
  Box,
  Cards
} from '@cloudscape-design/components';
import { getHowItWorksContent } from '../../utils/contentLoader';
import SectionContainer from './SectionContainer';

const HowItWorksTable = () => {
  const { title, description, personas } = getHowItWorksContent();

  return (
    <SectionContainer
      header={
        <Header
          variant="h2"
          description={description}
        >
          {title}
        </Header>
      }
    >
      <SpaceBetween size="l">

        <Cards
          cardDefinition={{
            header: item => (
              <Box variant="h3" fontSize="heading-m" padding="s">
                {item.title}
              </Box>
            ),
            sections: [
              {
                content: item => (
                  <Box variant="p" color="text-body-secondary" padding="s">
                    {item.description}
                  </Box>
                )
              }
            ]
          }}
          cardsPerRow={[
            { cards: 1 },
            { minWidth: 500, cards: 2 },
            { minWidth: 900, cards: 3 }
          ]}
          items={personas}
          trackBy="id"
          empty={
            <Box textAlign="center" color="inherit">
              <b>No information available</b>
            </Box>
          }
        />
      </SpaceBetween>
    </SectionContainer>
  );
};

export default HowItWorksTable;