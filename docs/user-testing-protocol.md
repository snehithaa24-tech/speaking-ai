# SAHAYAK AI User Testing Protocol

## Overview

This document defines the protocol for evaluating SAHAYAK AI with real users across English (India), Hindi, and Telugu languages.

## Objectives

1. Measure speech recognition accuracy (Word Error Rate) per language
2. Measure response latency (connection, first token, full response)
3. Evaluate task completion rates for core use cases
4. Assess error recovery and user confidence
5. Collect qualitative feedback on usability and accessibility

## Participant Recruitment

### Target Distribution (Minimum 10 Participants)

| Language | Count | Criteria |
|----------|-------|----------|
| Hindi | 3 | Native Hindi speakers, varied regions |
| Telugu | 3 | Native Telugu speakers, varied regions |
| English (India) | 2 | Indian English speakers |
| Accent/Dialect Varied | 2 | Regional accents, non-standard dialects |

### Inclusion Criteria
- Age 18-65
- Own smartphone/computer with microphone
- Comfortable with voice interaction
- No severe hearing impairment (for audio output testing)
- Able to provide informed consent

### Exclusion Criteria
- Professional voice actors
- Previous participation in SAHAYAK AI testing
- Cognitive impairments affecting task comprehension

### Recruitment Channels
- Community organizations
- University language departments
- Social media (targeted groups)
- Referral from participants

## Ethics & Consent

### Informed Consent
- Written consent form (digital or paper)
- Plain language explanation of:
  - Purpose of study
  - Data collected (audio, transcripts, metrics)
  - Data retention (30 days for research, then deleted)
  - Right to withdraw at any time
  - No compensation for participation (or nominal honorarium)

### Privacy
- No PII in evaluation records
- Audio recordings only with explicit opt-in
- Data stored on encrypted local storage during testing
- Anonymized before analysis

### IRB/ETHICS
- Document IRB approval or exemption
- Adhere to local data protection laws

## Test Environment

### Setup
- Quiet room (background noise < 40dB)
- Test device: Laptop with Chrome/Edge/Firefox
- External USB microphone (Blue Yeti or similar) for consistent input quality
- Headphones for participant (to hear assistant clearly)
- Screen recording software (OBS) for session capture

### Test Accounts
- Pre-configured test environment
- No authentication required
- Fresh session per participant

## Test Procedure

### 1. Onboarding (5 minutes)
- Welcome and introduction
- Sign consent form
- Demographic questionnaire:
  - Age range
  - Primary language
  - Region/dialect
  - Tech comfort level (1-5)
  - Prior voice assistant experience

### 2. Orientation (3 minutes)
- Show home screen
- Explain microphone button
- Demonstrate language selector
- Show accessibility settings
- Answer questions

### 3. Calibration (2 minutes)
- Participant selects preferred language
- Microphone test: "Please say: 'Hello, how are you?'"
- Adjust volume if needed
- Verify audio output works

### 4. Task Scenarios (20-25 minutes)

#### Task 1: Agriculture Query (3 min)
**Prompt**: "You want to know the best time to sow wheat in your region. Ask the assistant."
**Success Criteria**: Receives relevant sowing time information
**Language**: Participant's preferred language

#### Task 2: Government Scheme (4 min)
**Prompt**: "You heard about a scheme called PM-KISAN for farmers. Find out if you're eligible and how to apply."
**Success Criteria**: Gets eligibility criteria and application process
**Language**: Participant's preferred language

#### Task 3: Hospital Assistance (3 min)
**Prompt**: "You need to find a government hospital near you that has a cardiology department."
**Success Criteria**: Receives hospital search guidance (may not have real data)
**Language**: Participant's preferred language

#### Task 4: Transport Information (3 min)
**Prompt**: "You want to travel from your city to the state capital by bus. Ask for schedule and fare information."
**Success Criteria**: Gets transport query acknowledgment
**Language**: Participant's preferred language

#### Task 5: Language Switching (3 min)
**Prompt**: "Switch to English (or Hindi/Telugu if not English) and ask the same question from Task 1 again."
**Success Criteria**: Successfully switches language, gets response in new language
**Language**: Switch to different language

#### Task 6: Interruption & Recovery (3 min)
**Prompt**: "Ask a long question. When the assistant starts responding, interrupt it by speaking again."
**Success Criteria**: Assistant stops, listens to new input
**Language**: Participant's preferred language

#### Task 7: Repeat Request (2 min)
**Prompt**: "Ask the assistant to repeat its last answer."
**Success Criteria**: Assistant repeats previous response
**Language**: Participant's preferred language

#### Task 8: Accessibility Settings (2 min)
**Prompt**: "Enable large text mode and high contrast. Verify the UI changes."
**Success Criteria**: Settings applied correctly
**Language**: Any

### 5. Post-Task Questionnaire (5 minutes)

For each task, rate 1-5:
- Ease of completion
- Clarity of response
- Voice naturalness
- Confidence in answer

Overall:
- System Usability Scale (SUS) - 10 items
- Net Promoter Score (NPS) - 1 item
- Open feedback: "What worked well? What was frustrating?"

### 6. Debrief (3 minutes)
- Thank participant
- Answer questions
- Provide honorarium/contact info for follow-up

## Metrics Collection

### Automated Metrics (Per Task)

| Metric | Measurement |
|--------|-------------|
| Task Success | Binary (completed/failed) |
| Time to Complete | Seconds from first speech to success |
| Speech Recognition WER | Calculated from reference vs hypothesis |
| Connection Time | WebSocket connect to ready |
| First Token Latency | User speech end to first audio chunk |
| Full Response Latency | User speech end to last audio chunk |
| Interruption Success | Binary (assistant stopped) |
| Recovery Attempts | Count of re-tries needed |

### Word Error Rate Calculation

```
WER = (Substitutions + Deletions + Insertions) / Reference Words × 100%

Reference: "What is the best time to sow wheat?"
Hypothesis: "What is the best time to so wheat?"
Deletions: 1 ("w")
WER = 1/8 = 12.5%
```

Reference transcripts collected during testing by human transcriber.

### Language-Specific Reporting

Report WER separately for:
- English (en-IN)
- Hindi (hi-IN)
- Telugu (te-IN)

### Subjective Metrics

| Scale | Items |
|-------|-------|
| SUS | 10 items, score 0-100 |
| NPS | 1 item, -100 to +100 |
| Task Ease | 5-point Likert per task |
| Voice Quality | 5-point Likert per language |

## Data Recording

### Per-Session Log
```json
{
  "participant_id": "P001",
  "language": "hi-IN",
  "session_id": "uuid",
  "start_time": "2024-01-15T10:00:00Z",
  "end_time": "2024-01-15T10:35:00Z",
  "tasks": [
    {
      "task_id": "agriculture",
      "success": true,
      "duration_seconds": 45,
      "wer": 8.2,
      "latency": { "connection": 1.2, "first_token": 0.8, "full": 3.5 },
      "interruptions": 0,
      "recovery_attempts": 0
    }
  ],
  "sus_score": 82.5,
  "nps": 9,
  "feedback": "Voice was clear but sometimes too fast"
}
```

### Audio Recording (Opt-in)
- Filename: `P001_hi-IN_task1.wav`
- Stored locally during test
- Transcribed by human for WER calculation
- Deleted after analysis unless consent for retention

## Analysis Plan

### Quantitative Analysis

1. **WER by Language**
   - Mean, median, std dev per language
   - Compare to benchmarks (Google: ~5-8% for EN, ~10-15% for HI/TE)

2. **Latency Analysis**
   - Percentiles (p50, p90, p99) for each latency type
   - Target: First token < 1s, Full response < 3s

3. **Task Completion**
   - Success rate per task per language
   - Chi-square test for language differences

4. **SUS/NPS**
   - Mean SUS (target > 68)
   - NPS distribution

5. **Recovery Rate**
   - % of interruptions successfully handled
   - Mean recovery attempts

### Qualitative Analysis

- Thematic analysis of open feedback
- Affinity mapping of pain points
- Language-specific issues identification

### Statistical Significance

- Minimum 3 participants per language for descriptive stats
- 10+ total for cross-language comparison
- Report confidence intervals (95%)

## Reporting

### Deliverables

1. **Evaluation Report** (PDF)
   - Executive summary
   - Methodology
   - Quantitative results (tables, charts)
   - Qualitative findings
   - Recommendations

2. **Metrics Dashboard** (JSON/CSV)
   - Raw data for all participants
   - Calculated metrics
   - Per-language breakdown

3. **Presentation** (10 slides)
   - Key findings
   - Critical issues
   - Next steps

### Report Template

```markdown
# SAHAYAK AI User Evaluation Report

## Executive Summary
- N participants, X languages
- Overall SUS: XX
- Overall WER: XX%
- Critical findings: 3-5 bullets

## Methodology
- Participant demographics table
- Test environment
- Task descriptions

## Results

### Speech Recognition (WER)
| Language | N | Mean WER | Median | Std Dev |
|----------|---|----------|--------|---------|
| en-IN    | 2 | 6.2%     | 5.8%   | 1.2%    |
| hi-IN    | 3 | 12.4%    | 11.8%  | 2.1%    |
| te-IN    | 3 | 14.1%    | 13.5%  | 2.8%    |

### Latency (seconds)
| Metric | p50 | p90 | p99 | Target |
|--------|-----|-----|-----|--------|
| Connection | 0.8 | 1.5 | 2.2 | < 2s |
| First Token | 0.6 | 1.1 | 1.8 | < 1s |
| Full Response | 2.1 | 3.8 | 5.2 | < 3s |

### Task Completion
| Task | en-IN | hi-IN | te-IN | Overall |
|------|-------|-------|-------|---------|
| Agriculture | 100% | 100% | 67% | 89% |
| Government | 100% | 67% | 67% | 78% |
| Hospital | 100% | 100% | 100% | 100% |
| Transport | 50% | 33% | 33% | 39% |

### Usability
- SUS: Mean XX (SD X)
- NPS: XX

## Qualitative Findings
### Strengths
- Natural voice quality in Hindi
- Easy language switching
- Clear interruption handling

### Issues
1. Telugu recognition struggles with dialect words
2. Transport queries fail (no real API)
3. Volume control hard to find
4. Long responses hard to follow

## Recommendations
### Priority 1 (Blockers)
- Improve Telugu acoustic model
- Add real transport API integration

### Priority 2 (Improvements)
- Reduce response length
- Better volume control visibility
- Add "slow down" command

### Priority 3 (Nice to Have)
- More voice options
- Offline mode
```

## Timeline

| Phase | Duration |
|-------|----------|
| Protocol Finalization | 1 week |
| IRB/Consent Prep | 1 week |
| Recruitment | 2-3 weeks |
| Testing Sessions | 1-2 weeks |
| Transcription/Analysis | 1 week |
| Report Writing | 1 week |
| **Total** | **7-9 weeks** |

## Budget Estimate

| Item | Cost |
|------|------|
| Participant honorarium (10 × $50) | $500 |
| Transcription (10 hrs × $30/hr) | $300 |
| Equipment (mic, recording) | $200 |
| Analysis tools | $100 |
| **Total** | **~$1,100** |

## Consent Form Template

```
SAHAYAK AI User Testing - Informed Consent

Purpose: Evaluate a multilingual voice assistant for accessibility.

Procedures:
1. Complete demographic questionnaire (5 min)
2. Interact with voice assistant for 8 tasks (25 min)
3. Complete post-task questionnaire (5 min)

Data Collected:
- Audio recordings (with your permission)
- Transcripts of your speech
- System performance metrics
- Your ratings and feedback

Risks: Minimal. Possible frustration with voice recognition.

Benefits: Help improve accessibility technology.

Confidentiality: Data anonymized. Audio deleted after analysis unless you consent to retention.

Voluntary: You may withdraw at any time without penalty.

Contact: research@sahayak.ai

I have read and understand the above. I consent to participate.

Signature: _________________ Date: ___________

Audio Recording Consent (Optional):
☐ I consent to audio recording for research purposes
☐ I do NOT consent to audio recording

Signature: _________________ Date: ___________
```

## Checklist for Test Day

- [ ] Consent forms printed
- [ ] Demographic questionnaires printed
- [ ] Task cards printed
- [ ] Post-task questionnaires printed
- [ ] Device charged/connected
- [ ] Microphone tested
- [ ] Headphones ready
- [ ] Screen recording configured
- [ ] Test environment URL accessible
- [ ] Backup device ready
- [ ] Water for participants
- [ ] Honorarium envelopes prepared
- [ ] Emergency contact info available