# Agile Format Guidelines

## User Story Format Standard

### Core Structure
```
As a [role],
I want [feature],
So that [benefit]
```

### Writing Rules

**Role**:
- Use specific persona names (Product Manager, Business Analyst, End User)
- Avoid generic "user" when possible
- Match to defined personas

**Feature**:
- Start with action verb (enter, upload, generate, analyze)
- Be specific about what, not how
- One feature per story
- Keep to one sentence

**Benefit**:
- Articulate clear value
- Connect to business goals or user needs
- Make it measurable when possible
- Answer "why does this matter?"

---

## Acceptance Criteria Formats

### Format 1: Given-When-Then (Gherkin)

**When to Use**: User interactions, system behavior, event-driven scenarios

**Structure**:
```
Given [precondition/context]
When [action/trigger]
Then [expected result]
```

**Examples**:
```
Given I am on the login page
When I enter valid credentials
Then I am redirected to the dashboard

Given the system has processed requirements
When analysis completes
Then a summary document is generated
```

**Best Practices**:
- One scenario per criterion
- Be specific about context
- Clearly state the action
- Define observable outcome
- Avoid implementation details

### Format 2: Checklist

**When to Use**: Processing steps, validation rules, configuration requirements

**Structure**:
```
- [Criterion 1]
- [Criterion 2]
- [Criterion 3]
```

**Examples**:
```
- System accepts PDF, DOCX, and TXT file formats
- System extracts text content from uploaded documents
- System displays extracted content for review
- System handles files up to 10MB
```

**Best Practices**:
- Each item is independently testable
- Use active voice
- Be specific and measurable
- Avoid ambiguous terms
- Include quantifiable limits

---

## Acceptance Criteria Best Practices

### Coverage Requirements

**Normal Flow (3-5 criteria)**:
- Happy path scenarios
- Expected user interactions
- Standard system behavior
- Typical use cases

**Edge Cases (1-2 criteria)**:
- Boundary conditions
- Unusual but valid scenarios
- Minimum/maximum values
- Empty or null inputs

**Error Handling (1-2 criteria)**:
- Invalid inputs
- System failures
- Validation errors
- Exception scenarios

**Non-Functional Requirements (1-2 criteria)**:
- Performance expectations
- Security requirements
- Validation rules
- Data integrity

### Quality Characteristics

Each criterion must be:

**Specific**:
- ❌ "System works correctly"
- ✅ "System accepts text up to 50,000 characters"

**Testable**:
- ❌ "System is fast"
- ✅ "System responds within 2 seconds"

**Measurable**:
- ❌ "System handles errors well"
- ✅ "System displays error message when file exceeds 10MB"

**Unambiguous**:
- ❌ "System processes data appropriately"
- ✅ "System extracts text content from PDF documents"

---

## Story Naming Conventions

### Title Format
```
[Action] [Object] [Context]
```

**Examples**:
- "Provide Text Requirements"
- "Upload PRD Document"
- "Generate User Journeys"
- "Prioritize User Stories"

### Title Guidelines
- Start with verb (Provide, Upload, Generate, Analyze)
- Include object (Requirements, Document, Journeys)
- Add context if needed (for Clarity, with Validation)
- Keep under 60 characters
- Use title case

---

## Story Description Format

### Full Story Text
```
**Story ID**: [Unique identifier]

**Title**: [Story title]

**As a** [role],
**I want** [feature],
**So that** [benefit]

**Personas**: [Primary], [Secondary]

**Acceptance Criteria**:
[Format: Given-When-Then or Checklist]
1. [Criterion 1]
2. [Criterion 2]
3. [Criterion 3]
4. [Criterion 4]
5. [Criterion 5]

**NFR Acceptance Criteria** (if applicable):
- [Performance criterion]
- [Security criterion]
- [Validation criterion]

**Traceability**:
- Feature: [Feature name]
- Journey: [Journey name]
- Epic: [Epic name]

**Dependencies**: [List any blocking stories]

**Priority**: [High/Medium/Low]

**Estimate**: [Story points or time]
```

---

## Epic Format

### Epic Structure
```
**Epic Name**: [Descriptive name]

**Epic Description**: [2-3 sentence overview]

**Business Value**: [Why this epic matters]

**User Stories**: [List of stories in this epic]

**Acceptance Criteria**:
- [Epic-level criterion 1]
- [Epic-level criterion 2]
- [Epic-level criterion 3]

**Dependencies**: [Other epics or external dependencies]
```

### Epic Naming
- Use noun phrases (Input Processing, Journey Mapping)
- Describe functional area or capability
- Keep under 50 characters

---

## Feature Format

### Feature Structure
```
**Feature Name**: [Descriptive name]

**Description**: [What the feature does]

**User Stories**: [Stories implementing this feature]

**Linked Journeys**: [Journeys requiring this feature]

**Functional Area**: [Category]

**Priority**: [High/Medium/Low]
```

---

## Formatting Standards

### Markdown Usage

**Headers**:
```markdown
# Epic Name
## Feature Name
### Story Title
```

**Lists**:
```markdown
- Unordered item
- Unordered item

1. Ordered item
2. Ordered item
```

**Emphasis**:
```markdown
**Bold** for field names
*Italic* for emphasis
`Code` for technical terms
```

**Links**:
```markdown
[Story Title](#story-id)
[Feature Name](feature-link)
```

**Tables**:
```markdown
| Story ID | Feature | Priority |
|----------|---------|----------|
| S-001    | Input   | High     |
```

---

## Traceability Format

### Linking Structure
```
Requirement → Journey → Feature → Story → Acceptance Criteria
```

### Traceability Matrix
```markdown
| Story ID | Story Title | Feature | Journey | Persona | Priority |
|----------|-------------|---------|---------|---------|----------|
| S-001    | [Title]     | [Name]  | [Name]  | [Name]  | High     |
```

### Cross-Reference Format
```markdown
**Related Stories**: [S-002](#s-002), [S-003](#s-003)
**Depends On**: [S-001](#s-001)
**Blocks**: [S-005](#s-005)
```

---

## Priority Format

### Priority Levels
- **HIGH**: Critical for MVP, high business value, low risk
- **MEDIUM**: Important but not critical, moderate value/risk
- **LOW**: Nice to have, lower value, or higher risk

### Priority Documentation
```markdown
**Priority**: High

**Rationale**: 
- Critical for core functionality
- High business value (enables key workflow)
- Low technical risk
- No blocking dependencies
```

---

## Status Format

### Status Values
- **Backlog**: Not yet started
- **Ready**: Refined and ready for development
- **In Progress**: Currently being developed
- **In Review**: Code review or testing
- **Done**: Completed and accepted

### Status Tracking
```markdown
**Status**: In Progress
**Started**: 2026-01-10
**Assigned To**: [Developer name]
**Estimated Completion**: 2026-01-15
```

---

## Documentation Standards

### Story Documentation
- Use consistent formatting across all stories
- Include all required fields
- Link to related artifacts
- Keep descriptions concise
- Update status regularly

### Version Control
- Track story changes
- Document refinements
- Note acceptance criteria updates
- Record priority changes

### Review Process
- Product Owner reviews all stories
- Team reviews acceptance criteria
- Stakeholders validate value
- Technical lead reviews feasibility

---

## Common Formatting Mistakes

### ❌ Inconsistent Format
```
Story 1: As a user I want to...
Story 2: I want to... as a user
Story 3: User wants to...
```

### ✅ Consistent Format
```
Story 1: As a user, I want to...
Story 2: As a user, I want to...
Story 3: As a user, I want to...
```

### ❌ Vague Criteria
```
- System works correctly
- Performance is good
- Errors are handled
```

### ✅ Specific Criteria
```
- System accepts text up to 50,000 characters
- System responds within 2 seconds
- System displays error message when input is invalid
```

### ❌ Missing Traceability
```
Story with no links to features or journeys
```

### ✅ Complete Traceability
```
**Feature**: Input Processing
**Journey**: Requirements Collection
**Epic**: Input Processing
```

---

## Templates Quick Reference

### Minimal Story
```
As a [role],
I want [feature],
So that [benefit]

Acceptance Criteria:
1. [Criterion 1]
2. [Criterion 2]
3. [Criterion 3]
4. [Criterion 4]
5. [Criterion 5]
```

### Complete Story
```
**Story ID**: S-001
**Title**: [Story Title]

As a [role],
I want [feature],
So that [benefit]

**Personas**: [Primary], [Secondary]

**Acceptance Criteria**:
Given [context]
When [action]
Then [result]

[Additional criteria...]

**Traceability**:
- Feature: [Name]
- Journey: [Name]
- Epic: [Name]

**Priority**: [High/Medium/Low]
**Status**: [Backlog/In Progress/Done]
```
