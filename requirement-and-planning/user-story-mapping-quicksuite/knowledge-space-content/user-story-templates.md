# User Story Templates

## Standard Agile User Story Format

### Template Structure
```
As a [role/persona],
I want [feature/capability],
So that [benefit/value]
```

### Components Explained

**Role/Persona**: Who is this story for?
- Product Manager
- Business Analyst
- End User
- System Administrator
- Developer

**Feature/Capability**: What do they want?
- Be specific and action-oriented
- Focus on the "what" not the "how"
- Keep it concise (one sentence)

**Benefit/Value**: Why do they want it?
- Clear business or user value
- Measurable outcome when possible
- Connects to business goals

---

## Example User Stories

### Example 1: Input Processing
```
As a Product Manager,
I want to enter requirements as text directly into the system,
So that I can quickly input requirements without creating a document
```

### Example 2: Analysis
```
As a Business Analyst,
I want the system to analyze provided requirements,
So that I can understand the scope and complexity of the project
```

### Example 3: Output Generation
```
As a Product Manager,
I want the system to generate a comprehensive markdown document,
So that I have all artifacts in a single, shareable format
```

---

## Acceptance Criteria Templates

### Given-When-Then Format
Use for user interactions and system behavior:

```
Given [initial context/state]
When [action/event occurs]
Then [expected outcome]
```

**Examples**:
```
Given I am on the input screen
When I enter requirements text
Then the system accepts text up to 50,000 characters

Given I have entered requirements text
When I submit the input
Then the system displays a confirmation message
```

### Checklist Format
Use for processing steps and validation:

```
- [Criterion 1]
- [Criterion 2]
- [Criterion 3]
```

**Examples**:
```
- System analyzes requirements text using AI
- System identifies key features mentioned in requirements
- System identifies user roles and personas from requirements
- System generates analysis summary document
```

---

## Acceptance Criteria Guidelines

### Quantity
- **Minimum**: 5 criteria per story
- **Maximum**: 10 criteria per story
- **Recommended**: 6-8 criteria for balanced coverage

### Coverage Distribution
- **Normal Flow**: 3-5 criteria (happy path scenarios)
- **Edge Cases**: 1-2 criteria (boundary conditions, unusual scenarios)
- **Error Handling**: 1-2 criteria (validation failures, exceptions)
- **NFRs**: 1-2 criteria (performance, security, validation)

### Quality Characteristics
Each criterion should be:
- **Specific**: Clear and unambiguous
- **Testable**: Can be verified objectively
- **Measurable**: Has clear pass/fail conditions
- **Independent**: Can be tested separately
- **Complete**: Covers all aspects of the requirement

---

## Story Quality Checklist (INVEST)

### Independent
- ✅ Story can be developed without dependencies on other stories
- ✅ Story can be delivered independently
- ✅ Story doesn't require other stories to be complete first

### Negotiable
- ✅ Details can be discussed and refined
- ✅ Implementation approach is flexible
- ✅ Story is not a contract with fixed details

### Valuable
- ✅ Provides clear value to users or business
- ✅ Value is articulated in the "so that" clause
- ✅ Stakeholders understand the benefit

### Estimable
- ✅ Team can estimate effort required
- ✅ Scope is clear enough to size
- ✅ Technical approach is understood

### Small
- ✅ Can be completed in one iteration/sprint
- ✅ Not too large to manage
- ✅ Can be broken down if needed

### Testable
- ✅ Has clear acceptance criteria
- ✅ Success can be verified
- ✅ Pass/fail conditions are defined

---

## Story Sizing Guidelines

### Small Stories (1-3 days)
- Single feature or capability
- Clear scope and requirements
- Minimal dependencies
- Straightforward implementation

### Medium Stories (3-5 days)
- Multiple related features
- Some complexity or unknowns
- Few dependencies
- Standard implementation

### Large Stories (5+ days)
- Complex features or capabilities
- Significant unknowns
- Multiple dependencies
- **Recommendation**: Break into smaller stories

---

## Common Story Patterns

### CRUD Operations
```
As a [role],
I want to [create/read/update/delete] [entity],
So that I can [manage/track/maintain] [business object]
```

### Data Processing
```
As a [role],
I want the system to [process/analyze/transform] [data],
So that I can [gain insights/make decisions/take action]
```

### Integration
```
As a [role],
I want to [integrate/connect/sync] with [external system],
So that I can [share data/automate workflow/reduce manual work]
```

### Reporting
```
As a [role],
I want to [view/generate/export] [report/dashboard],
So that I can [monitor/analyze/share] [metrics/insights]
```

---

## Anti-Patterns to Avoid

### ❌ Technical Implementation Details
```
As a developer,
I want to implement a REST API with JWT authentication,
So that the system is secure
```
**Why**: Focuses on "how" not "what" or "why"

### ❌ Too Vague
```
As a user,
I want the system to work well,
So that I'm happy
```
**Why**: Not specific, not testable, no clear value

### ❌ Multiple Features
```
As a user,
I want to upload documents, analyze them, generate reports, and export to PDF,
So that I can do everything
```
**Why**: Too large, should be multiple stories

### ❌ No Clear Benefit
```
As a user,
I want to click a button,
So that something happens
```
**Why**: No clear value articulated

---

## Story Refinement Process

### Initial Draft
- Write basic story structure
- Identify role, feature, benefit
- Keep it simple

### Add Acceptance Criteria
- Define 5-10 testable criteria
- Cover normal flow, edge cases, errors, NFRs
- Use appropriate format (Given-When-Then or checklist)

### Review Against INVEST
- Check each INVEST criterion
- Refine as needed
- Split if too large

### Add Traceability
- Link to feature
- Link to user journey
- Link to persona
- Link to requirements

### Validate with Stakeholders
- Review with product owner
- Confirm value and priority
- Adjust based on feedback

---

## Story Metadata

### Required Fields
- **Story ID**: Unique identifier
- **Title**: Short descriptive name
- **Description**: Full story text (As a... I want... So that...)
- **Acceptance Criteria**: 5-10 testable criteria
- **Priority**: High/Medium/Low
- **Status**: Backlog/In Progress/Done

### Optional Fields
- **Epic**: Parent epic
- **Feature**: Parent feature
- **Persona**: Primary user persona
- **Estimate**: Story points or time
- **Dependencies**: Blocking/blocked by
- **Tags**: Labels for categorization
- **Traceability**: Links to requirements, journeys

---

## Templates by Story Type

### Feature Story
```
As a [user role],
I want to [new capability],
So that I can [achieve goal]

Acceptance Criteria:
- Feature is accessible from [location]
- Feature performs [action] when [condition]
- Feature displays [result] after [action]
- Feature handles [edge case] by [behavior]
- Feature validates [input] and shows [error message]
```

### Bug Fix Story
```
As a [user role],
I want [incorrect behavior] to be fixed,
So that I can [work without issues]

Acceptance Criteria:
- Bug is reproducible with [steps]
- Root cause is identified
- Fix resolves the issue
- Fix doesn't introduce regressions
- Fix is tested in [environments]
```

### Technical Story
```
As a [developer/team],
I want to [technical improvement],
So that [technical benefit]

Acceptance Criteria:
- Implementation follows [standards]
- Code is reviewed and approved
- Tests are written and passing
- Documentation is updated
- Performance meets [criteria]
```

### Spike Story (Research)
```
As a [team],
I want to investigate [topic/technology],
So that we can [make informed decision]

Acceptance Criteria:
- Research covers [areas]
- Findings are documented
- Recommendations are provided
- Risks are identified
- Decision is made
```
