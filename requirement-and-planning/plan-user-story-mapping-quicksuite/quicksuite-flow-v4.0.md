# User Story Mapping Generator - QuickSuite Flow

## Overview
Automates user story mapping from requirements: generates user journeys, identifies gaps, and prioritizes stories by business value.

## Flow Steps

### 1. Upload Requirements Document
**Type**: File upload
**Title**: Requirements Document (PRD/BRD)
**Label**: Upload requirements (PDF, DOCX, TXT, MD)
**Output**: @Requirements Document

---

### 2. Requirements Analysis
**Type**: Quick Suite data
**Space**: Product Management Best Practices
**Dependencies**: [@Requirements Document]
**Prompt**:
```
Analyze @Requirements Document and extract:

1. **User Behaviors**: Key user actions, workflows, and interaction patterns
2. **Business Requirements**: Core features, capabilities, and business goals
3. **Success Criteria**: Measurable outcomes and business value indicators
4. **User Personas**: Roles, goals, and pain points mentioned

Focus on identifying:
- Primary user workflows and journeys
- Feature requirements and capabilities
- Business value and impact areas
- User types and their needs

Output structured analysis with:
- User Behaviors: [List key workflows]
- Business Requirements: [List features/capabilities]
- Success Criteria: [List measurable outcomes]
- User Personas: [List roles and characteristics]
```
**Output Variables**: 
- userBehaviors
- businessRequirements
- successCriteria
- userPersonas

---

### 3. User Journey Mapping & Gap Analysis
**Type**: Quick Suite data
**Space**: Product Management Best Practices
**Dependencies**: [Requirements Analysis]
**Prompt**:
```
Based on Requirements Analysis, create user journey maps and identify gaps:

1. **User Journey Maps**: Map complete user workflows from start to finish
   - Journey Name: [Name]
   - Steps: [Sequential user actions]
   - Touchpoints: [System interactions]
   - Pain Points: [Issues or friction]

2. **Gap Analysis**: Identify missing elements
   - Missing Features: Features needed but not specified
   - Missing Steps: Workflow steps not covered
   - Edge Cases: Scenarios not addressed
   - Integration Gaps: External system needs

3. **Feature List**: Comprehensive features needed
   - Core Features: Essential capabilities
   - Supporting Features: Additional functionality
   - Gap-Filling Features: Address identified gaps

Analysis Data:
- User Behaviors: {userBehaviors}
- Business Requirements: {businessRequirements}
- User Personas: {userPersonas}

Output format:
## User Journey Maps
[Journey 1]
[Journey 2]
...

## Gap Analysis
**Missing Features**: [List]
**Missing Steps**: [List]
**Edge Cases**: [List]

## Complete Feature List
[All features needed]
```
**Output Variables**:
- userJourneys
- gapAnalysis
- featureList

---

### 4. User Stories Generation & Prioritization
**Type**: Quick Suite data
**Space**: Product Management Best Practices
**Dependencies**: [Requirements Analysis, User Journey Mapping & Gap Analysis]
**Prompt**:
```
Generate prioritized user stories with acceptance criteria:

**Format per story**:
**As a** [persona], **I want** [feature] **so that** [business value]

**Acceptance Criteria:**
- Given [context], When [action], Then [outcome]
- [Additional criteria]

**Priority**: [P0/P1/P2 - based on business impact]
**Business Value**: [High/Medium/Low - impact on success criteria]
**Journey Mapping**: [Links to user journey]
**Addresses Gap**: [Yes/No - fills identified gap]

**Prioritization Factors**:
1. Business value and ROI
2. User impact and frequency
3. Dependency on other features
4. Risk and complexity
5. Gap-filling importance

Analysis Data:
- User Journeys: {userJourneys}
- Gap Analysis: {gapAnalysis}
- Feature List: {featureList}
- Success Criteria: {successCriteria}
- User Personas: {userPersonas}

Generate 10-20 user stories covering:
- Core user journeys (P0)
- Gap-filling features (P0-P1)
- Supporting capabilities (P1-P2)
- Edge cases and enhancements (P2)

Group by priority and include traceability to journeys and gaps.
```
**Output Variable**: userStories

---

### 5. Document Creation
**Type**: Document generation
**Dependencies**: [User Stories Generation & Prioritization]
**Prompt**:
```
Create comprehensive user story mapping document:

# User Story Mapping Results
**Date**: {currentDate}
**Source**: {fileName}

## Executive Summary
[Brief overview of user journeys, gaps identified, and story count by priority]

## User Journey Maps
{userJourneys}

## Gap Analysis
{gapAnalysis}

## Prioritized User Stories
{userStories}

## Traceability Matrix
[Map stories to journeys, features, and gaps]

## Next Steps
- [ ] Review and validate user stories with stakeholders
- [ ] Refine priorities based on team capacity
- [ ] Break down P0 stories for sprint planning
- [ ] Schedule backlog grooming session
```
**Action**: Create document
**Output**: User Story Mapping Document

---

## Key Features

**Automated Capabilities**:
1. ✅ User journey mapping from requirements
2. ✅ Gap identification (missing features, steps, edge cases)
3. ✅ User story generation with acceptance criteria
4. ✅ Priority-based ranking by business value
5. ✅ Traceability (journeys → features → stories)

**Workflow**: Requirements → Analysis → Journey Mapping → Gap Analysis → Story Generation → Prioritization → Documentation

**Output**: Complete user story map with priorities, gaps, and traceability
