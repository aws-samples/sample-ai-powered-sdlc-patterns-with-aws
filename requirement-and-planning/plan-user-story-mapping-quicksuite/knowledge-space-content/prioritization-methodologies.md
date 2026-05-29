# Prioritization Methodologies

## Multi-Factor Prioritization Framework

### Four-Factor Model

**Factor 1: Business Value (40% weight)**
- Impact on business goals
- User satisfaction impact
- Revenue/cost impact
- Strategic alignment

**Factor 2: Effort Estimation (25% weight)**
- Development complexity
- Time required
- Resource requirements
- Technical challenges

**Factor 3: Risk Assessment (20% weight)**
- Technical risk
- Business risk
- Uncertainty level
- Dependencies on unknowns

**Factor 4: Dependencies (15% weight)**
- Prerequisites
- Blocking relationships
- Integration dependencies
- Sequence constraints

---

## Priority Calculation Method

### Scoring System (1-100 scale)

**Business Value Score (0-40 points)**:
- Critical to business goals: 40 points
- High business impact: 30 points
- Moderate business impact: 20 points
- Low business impact: 10 points
- Minimal business impact: 5 points

**Effort Score (0-25 points)**:
- Very low effort (1-2 days): 25 points
- Low effort (3-5 days): 20 points
- Moderate effort (1-2 weeks): 15 points
- High effort (2-4 weeks): 10 points
- Very high effort (1+ months): 5 points

**Risk Score (0-20 points)**:
- Very low risk: 20 points
- Low risk: 15 points
- Moderate risk: 10 points
- High risk: 5 points
- Very high risk: 2 points

**Dependency Score (0-15 points)**:
- No dependencies: 15 points
- Few dependencies: 12 points
- Some dependencies: 9 points
- Many dependencies: 6 points
- Blocked by dependencies: 3 points

### Total Priority Score
```
Priority Score = Business Value + Effort + Risk + Dependencies
Range: 0-100 points
```

### Priority Levels
- **HIGH**: 70-100 points
- **MEDIUM**: 40-69 points
- **LOW**: 0-39 points

---

## Business Value Assessment

### Value Dimensions

**User Impact**:
- How many users affected?
- How frequently used?
- How critical to user workflow?
- What's the impact if missing?

**Business Goals**:
- Supports strategic objectives?
- Enables revenue generation?
- Reduces operational costs?
- Improves competitive position?

**Market Positioning**:
- Required for market entry?
- Differentiates from competitors?
- Meets customer expectations?
- Addresses market trends?

### Value Scoring Guide

**Critical (40 points)**:
- Affects all users daily
- Blocks core business function
- Required for MVP
- High revenue impact

**High (30 points)**:
- Affects most users frequently
- Important business function
- Significant user satisfaction impact
- Moderate revenue impact

**Moderate (20 points)**:
- Affects some users regularly
- Useful business function
- Noticeable user benefit
- Some revenue impact

**Low (10 points)**:
- Affects few users occasionally
- Nice-to-have function
- Minor user benefit
- Minimal revenue impact

---

## Effort Estimation

### Estimation Factors

**Complexity**:
- Algorithm complexity
- Data model complexity
- Integration complexity
- UI/UX complexity

**Scope**:
- Number of components affected
- Number of systems involved
- Amount of code to write
- Testing requirements

**Unknowns**:
- New technology?
- Unclear requirements?
- External dependencies?
- Research needed?

### Effort Scoring Guide

**Very Low (25 points)**: 1-2 days
- Simple change
- Well-understood
- No dependencies
- Minimal testing

**Low (20 points)**: 3-5 days
- Straightforward implementation
- Clear requirements
- Few dependencies
- Standard testing

**Moderate (15 points)**: 1-2 weeks
- Moderate complexity
- Some unknowns
- Some dependencies
- Comprehensive testing

**High (10 points)**: 2-4 weeks
- High complexity
- Significant unknowns
- Many dependencies
- Extensive testing

**Very High (5 points)**: 1+ months
- Very complex
- Major unknowns
- Critical dependencies
- Full regression testing

---

## Risk Assessment

### Risk Categories

**Technical Risk**:
- New technology or framework
- Complex algorithms
- Performance concerns
- Scalability challenges
- Integration complexity

**Business Risk**:
- Unclear requirements
- Changing priorities
- Stakeholder disagreement
- Market uncertainty
- Competitive pressure

**Dependency Risk**:
- External system dependencies
- Third-party service dependencies
- Team dependencies
- Data dependencies
- Infrastructure dependencies

### Risk Scoring Guide

**Very Low (20 points)**:
- Proven technology
- Clear requirements
- No external dependencies
- Low complexity

**Low (15 points)**:
- Familiar technology
- Well-defined requirements
- Few external dependencies
- Moderate complexity

**Moderate (10 points)**:
- Some new technology
- Some requirement uncertainty
- Some external dependencies
- Moderate-high complexity

**High (5 points)**:
- Significant new technology
- Unclear requirements
- Many external dependencies
- High complexity

**Very High (2 points)**:
- Unproven technology
- Very unclear requirements
- Critical external dependencies
- Very high complexity

---

## Dependency Analysis

### Dependency Types

**Prerequisite Dependencies**:
- Must be completed before this story
- Blocks this story from starting
- Technical foundation required
- Data or infrastructure needed

**Blocking Dependencies**:
- This story blocks other stories
- Other stories waiting on this
- Critical path item
- Enables downstream work

**Integration Dependencies**:
- Requires external system
- Needs API or service
- Depends on third-party
- Requires data from elsewhere

**Resource Dependencies**:
- Requires specific expertise
- Needs specialized tools
- Requires access or permissions
- Needs specific environment

### Dependency Scoring Guide

**No Dependencies (15 points)**:
- Completely independent
- Can start immediately
- No blocking issues
- Self-contained

**Few Dependencies (12 points)**:
- 1-2 minor dependencies
- Can work around if needed
- Minimal blocking risk
- Mostly self-contained

**Some Dependencies (9 points)**:
- 3-4 dependencies
- Some blocking risk
- Requires coordination
- Partially dependent

**Many Dependencies (6 points)**:
- 5+ dependencies
- Significant blocking risk
- Requires extensive coordination
- Highly dependent

**Blocked (3 points)**:
- Cannot start yet
- Waiting on critical dependencies
- High blocking risk
- Completely dependent

---

## Prioritization Matrix

### Value vs. Effort Matrix

|              | Low Effort | Medium Effort | High Effort |
|--------------|------------|---------------|-------------|
| **High Value** | Quick Wins | Major Projects | Strategic |
| **Medium Value** | Fill-ins | Evaluate | Reconsider |
| **Low Value** | Maybe | Probably Not | Avoid |

**Quick Wins**: High value, low effort - Do first
**Major Projects**: High value, high effort - Plan carefully
**Strategic**: High value, very high effort - Long-term investment
**Fill-ins**: Medium value, low effort - Do when capacity available
**Evaluate**: Medium value, medium effort - Assess carefully
**Reconsider**: Medium value, high effort - Question if worth it
**Maybe**: Low value, low effort - Only if extra capacity
**Probably Not**: Low value, medium effort - Likely skip
**Avoid**: Low value, high effort - Don't do

---

## Priority Rationale Template

```markdown
## Story: [Story Title]

**Priority**: [High / Medium / Low]
**Priority Score**: [0-100]

### Business Value (Score: [0-40])
- **User Impact**: [Description]
- **Business Goals**: [How it supports goals]
- **Market Positioning**: [Competitive context]
- **Value Justification**: [Why this score]

### Effort Estimation (Score: [0-25])
- **Complexity**: [Assessment]
- **Scope**: [Size estimate]
- **Unknowns**: [Uncertainties]
- **Effort Justification**: [Why this score]

### Risk Assessment (Score: [0-20])
- **Technical Risk**: [Assessment]
- **Business Risk**: [Assessment]
- **Dependency Risk**: [Assessment]
- **Risk Justification**: [Why this score]

### Dependencies (Score: [0-15])
- **Prerequisites**: [List]
- **Blocking**: [What this blocks]
- **Integration**: [External dependencies]
- **Dependency Justification**: [Why this score]

### Overall Rationale
[Comprehensive explanation of priority decision]

### Recommendations
- **Timing**: [When to implement]
- **Sequence**: [Order relative to other stories]
- **Considerations**: [Special factors]
```

---

## Alternative Prioritization Methods

### MoSCoW Method

**Must Have**: Critical, non-negotiable
**Should Have**: Important, high value
**Could Have**: Desirable, nice to have
**Won't Have**: Out of scope for now

### RICE Scoring

**Reach**: How many users affected
**Impact**: How much it helps each user
**Confidence**: How sure are we
**Effort**: How much work required

Score = (Reach × Impact × Confidence) / Effort

### Kano Model

**Basic Needs**: Expected features (dissatisfiers if missing)
**Performance Needs**: More is better (satisfiers)
**Excitement Needs**: Unexpected delighters

### Weighted Shortest Job First (WSJF)

Score = (Business Value + Time Criticality + Risk Reduction) / Job Size

---

## Prioritization Best Practices

### Do's
✅ Involve stakeholders in prioritization
✅ Use objective criteria
✅ Document rationale
✅ Review priorities regularly
✅ Consider dependencies
✅ Balance quick wins and strategic items
✅ Communicate priorities clearly

### Don'ts
❌ Prioritize based on who asks loudest
❌ Ignore effort estimates
❌ Skip risk assessment
❌ Forget about dependencies
❌ Set everything as high priority
❌ Never revisit priorities
❌ Make decisions in isolation

---

## Priority Review Process

### When to Review
- Sprint planning
- Quarterly planning
- After major releases
- When priorities change
- When new information emerges

### Review Checklist
- [ ] Business value still accurate?
- [ ] Effort estimates still valid?
- [ ] Risk assessment still current?
- [ ] Dependencies changed?
- [ ] Market conditions changed?
- [ ] User needs evolved?
- [ ] Strategic goals shifted?

### Reprioritization Triggers
- New competitive threat
- Customer feedback
- Technical discovery
- Resource changes
- Market shifts
- Strategic pivot
- Dependency resolution

---

## Prioritization Examples

### Example 1: High Priority Story
```
Story: User Login Authentication
Business Value: 40 (Critical - blocks all features)
Effort: 20 (Low - 3-5 days)
Risk: 15 (Low - proven technology)
Dependencies: 15 (No dependencies)
Total Score: 90 (HIGH)

Rationale: Essential for any user interaction, low effort, low risk, no blockers. Must do first.
```

### Example 2: Medium Priority Story
```
Story: Export Data to CSV
Business Value: 20 (Moderate - useful but not critical)
Effort: 20 (Low - 3-5 days)
Risk: 15 (Low - straightforward)
Dependencies: 9 (Depends on data model)
Total Score: 64 (MEDIUM)

Rationale: Useful feature, easy to implement, but not critical. Do after high priority items.
```

### Example 3: Low Priority Story
```
Story: Custom Dashboard Themes
Business Value: 10 (Low - nice to have)
Effort: 10 (High - 2-4 weeks)
Risk: 10 (Moderate - UI complexity)
Dependencies: 6 (Many UI dependencies)
Total Score: 36 (LOW)

Rationale: Low value, high effort, moderate risk. Consider for future release.
```

---

## Stakeholder Communication

### Priority Communication Template
```
## Priority Summary

**High Priority (Do First)**:
- [Count] stories
- [Key stories list]
- Rationale: [Why these are critical]

**Medium Priority (Do Next)**:
- [Count] stories
- [Key stories list]
- Rationale: [Why these are important]

**Low Priority (Do Later)**:
- [Count] stories
- [Key stories list]
- Rationale: [Why these are deferred]

**Deferred (Not Now)**:
- [Count] stories
- [Key stories list]
- Rationale: [Why these are out of scope]
```
