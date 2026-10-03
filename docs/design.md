# Playbook: Design Document

## Overview

Playbook is an AI planner for a high school freshman. Version 1 combines his Schoology deadlines and personal commitments into one realistic daily schedule, then adjusts that schedule based on what he actually gets done.

The design follows a solutions architect process:

1. Requirements
2. Constraints, assumptions, and scope
3. Components and data flow
4. Service selection
5. Architecture diagram
6. Well-Architected review

## Step 1: Requirements

### Functional Requirements

| ID | Requirement |
|----|-------------|
| FR1 | The app syncs his assignments and due dates from Schoology every night. |
| FR2 | He can add non-school commitments (sports, debate, social events) alongside schoolwork. |
| FR3 | Opening the app shows today's schedule first. |
| FR4 | The planner builds a weekly plan that schedules work as early as possible before each deadline, without exceeding a daily workload limit. |
| FR5 | He can rearrange his schedule, but the app prevents changes that would cause him to miss a hard deadline, whether school or extracurricular. |
| FR6 | He can check off tasks as he completes them. |
| FR7 | Items are color coded by priority. |
| FR8 | Items become more visually urgent as their deadlines approach. |
| FR9 | The app sends one reminder email at 5pm the evening before, listing unchecked school tasks due the next day. |
| FR10 | Unfinished tasks move to the top of his list. |
| FR11 | When a task is late, he must choose a reason ("rather not say" is an option). |
| FR12 | The planner uses his history of late tasks and reasons to schedule future tasks more effectively. |

### Non-Functional Requirements

| ID | Category | Requirement |
|----|----------|-------------|
| NFR1 | Performance | Today's schedule loads quickly on his phone. |
| NFR2 | Availability | Offline viewing of today's schedule. *(Moved to v2.)* |
| NFR3 | Usability | Checking off a task takes a single tap. |
| NFR4 | Security | Only he can view his data in the app; admin access is limited to maintenance. |
| NFR5 | Reliability | His data is backed up, and past items can be recovered. |
| NFR6 | Cost | Total monthly cost stays under $15. |


## Step 2: Constraints, Assumptions, and Scope

### Constraints

1. Monthly cost must stay under $15.
2. v1 must be complete by mid-November.
3. Solo builder with limited Python and AI/ML experience.
4. Limited weekly build time alongside a full-time job and certification prep.
5. No Swift experience and no budget for an Apple developer account.
6. The user is a minor.
7. Existing AWS account is converting from Free Tier to paid.

### Decisions Driven by Constraints

- **Mobile-friendly web app instead of a native iPhone app** (constraints 1, 3, 5)
- **Parents informed, plus a privacy notice at account creation** explaining that admin access is for maintenance only (constraint 6)
- **AWS Budgets alerts and Cost Anomaly Detection set up before building anything** (constraints 1, 7)

### Assumptions

| ID | Assumption | How to Verify |
|----|------------|---------------|
| A1 | The Schoology iCal feed works, includes all classes, and updates when teachers change assignments. | Inspect the feed, then recheck after a teacher changes something. |
| A2 | The feed provides only assignment titles, courses, and due dates. | Inspect the feed. |
| A3 | The AI can estimate time needed from the course and assignment title, and he'll correct wrong estimates. | Test on real assignment titles and ask him if the estimates feel right. |
| A4 | He'll actually enter his non-school commitments. | Check after his first week. |
| A5 | He'll use the app only if it's very simple. | Watch him use it for a week and ask what annoyed him. |
| A6 | He'll have internet access whenever he uses the app. | Ask where and when he'd check it. |
| A7 | AI usage for one user fits within the $15 budget. | Track cost daily for the first two weeks. |
| A8 | Sign-in will use a personal account, since school accounts may block outside apps. | Test sign-in with his account. |

### Out of Scope for v1

- Offline access (v2)
- Concept coach for free-response practice (v2)
- Additional users (v2 or later)
- Gamification (decided after v1 feedback)
- Native iPhone app
- Schoology API integration (requires school admin approval)
- Mistake logging and SAT prep layer (v3)
- Push notifications, text messages, and reminder preferences for non-school tasks (v2)
