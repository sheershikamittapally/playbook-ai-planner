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


## Step 3: Components and Data Flow

### Components

| # | Component | Job |
|---|-----------|-----|
| 1 | App (front end) | What he sees and taps; reads from the stores when he views a screen |
| 2 | Sign-in | Confirms who he is |
| 3 | User Profile Store | Privacy notice acceptance, email address, and settings |
| 4 | Protected Link Storage | Keeps the Schoology calendar link safe, since it works like a password |
| 5 | Scheduler | Wakes up parts of the system at set times (2am sync and planning, 5pm reminders) |
| 6 | Calendar Sync | Fetches the Schoology feed and saves new or changed assignments |
| 7 | Task Store | Source of truth: assignments, his added items, completions with timestamps, late reasons, submission dates |
| 8 | Planner (AI) | Reads the Task Store, builds the next 7 days, saves the plan |
| 9 | Plan Store | Derived data: the finished plan, always rebuildable from the Task Store |
| 10 | Conflict Check | Warns him when a new item overlaps today's plan |
| 11 | Reminder Check | Finds unchecked school tasks due tomorrow |
| 12 | Email Sender | Delivers the reminder email |

### Scenarios

**Scenario 1: Account creation**
- He opens the app → *App* sends him to *Sign-in* → *Sign-in* confirms him → tells *App* he's verified
- First time only: *App* shows the privacy notice → he accepts → saved to *User Profile Store*
- He pastes his Schoology link → saved to *Protected Link Storage*

**Scenario 2: Overnight planning and morning view**
- At 2am Eastern → *Scheduler* triggers *Calendar Sync*
- *Calendar Sync* → reads the link from *Protected Link Storage* → fetches the feed → compares it to saved data → saves new or changed assignments to *Task Store*
- When sync finishes → *Scheduler* triggers *Planner*
- *Planner* → reads unfinished tasks, deadlines, his added items, and late history from *Task Store* → builds the next 7 days → saves to *Plan Store*
- In the morning, he opens the app → *Sign-in* → *App* reads today's plan from *Plan Store* (no AI call)

**Scenario 3: He adds a new commitment**
- He saves it → *Task Store* (no AI call)
- *Conflict Check* → warns him if it overlaps today's plan
- *App* → shows it right away when he views that day
- That night → *Planner* folds it into the plan

**Scenario 4: He checks off a task**
- He checks it off → saved to *Task Store* as done, with a timestamp → *App* shows it done right away
- If past due → required "why late" dropdown → reason saved with the task
- That night → *Planner* skips done tasks and uses late reasons when planning

**Scenario 5: A task goes overdue**
- *App* → marks a task overdue when displaying it (due date passed, not done; simple rule, no AI)
- That night → *Planner* moves overdue tasks to the top of the plan
- Late reason options: already done but forgot to check off, overwhelmed, had to prioritize something else, didn't want to, skipped it, cancelled assignment, already submitted (with submission date), rather not say
- After 7 days overdue → *App* shows these in a separate "older overdue" view, filtered from *Task Store* rather than copied → *Planner* skips them

**Scenario 6: Reminders**
- At 5pm → *Scheduler* triggers *Reminder Check*
- *Reminder Check* → reads *Task Store* for unchecked school tasks due tomorrow → bundles them into one message
- *Email Sender* → reads his address from *User Profile Store* → sends the email

### Design Principles

- **Precompute the plan overnight.** Opening the app is fast, and the AI is called once per night no matter how often he checks.
- **User input always goes to the source of truth.** The Plan Store is only ever rebuilt by the Planner.
- **The Planner only reads the Task Store and only writes to the Plan Store.**
- **Use AI only where judgment is needed.** Simple rules handle everything else (overdue checks, conflicts, reminders).
- **One job per component.** If Calendar Sync fails, the Planner still works from existing data.
- **Filter data instead of copying it**, to keep one source of truth.
- **Reuse existing components.** The Scheduler handles both nightly planning and reminders.
- **No background polling for a single user**, to keep costs down.

### UI Ideas

1. Today's schedule is the first screen after sign-in; he can close it to reach the home screen.
2. Home screen icons: calendar, profile, and a + button to add an item.
3. Add-item form: day, time, title, and how long it'll take.
4. Color coding by priority, getting darker and more urgent as deadlines approach.
5. Overdue items pinned to the top.
6. One-tap check-off.
7. "Why late" dropdown when checking off something past due.
8. "Older overdue" view for tasks more than 7 days late.
9. Conflict warning when a new item overlaps today's plan.
10. First sign-in screens: privacy notice, then pasting the Schoology link.
11. Overall feel: simple and calm, not addictive or gamified.


## Step 4: Service Selection

### New Component Identified

**13. API Layer:** the front end can't talk to the data stores directly without exposing the database to the internet, so an API layer sits between the App and everything behind it.

### Service Choices

| # | Component | Service | Why | Alternatives Considered |
|---|-----------|---------|-----|-------------------------|
| 1 | App hosting | S3 + CloudFront | Learning how the pieces fit together; more hands-on than a fully managed option | Amplify Hosting |
| 2 | API layer | API Gateway + Lambda | Serverless and pay-per-request; pairs naturally with the Lambda backend | AppSync (GraphQL adds new learning on a tight timeline) |
| 3 | Sign-in | Cognito | Supports Google sign-in without storing or handling passwords | Custom login |
| 4 | User Profile, Task, and Plan Stores | DynamoDB (on-demand, 3 tables) | Serverless, pay-per-request, pennies at one user's scale; three tables keep it simple | RDS/Aurora (always-on, would strain the $15 budget) |
| 5 | Protected Link Storage | Parameter Store (SecureString) | Standard parameters are free; one secret doesn't justify per-secret pricing | Secrets Manager |
| 6 | Scheduler | EventBridge Scheduler | Fires only at 2am and 5pm; pay per run with nothing running all day | Cron on an EC2 instance |
| 7 | Calendar Sync, Planner, Reminder Check, Conflict Check | Lambda | Each job runs seconds to a minute, a few times a day; pay only for run time | EC2, Fargate |
| 8 | Sync → Planner orchestration | Step Functions | Keeps them decoupled; Planner still runs from existing data if Sync fails | One Lambda calling the next |
| 9 | Planner AI | Bedrock (Claude Haiku) | Small, fast, good at reasoning; minimal cost at one call per night | Amazon Nova Lite (to be compared on real assignments; tests A3 and A7) |
| 10 | Email Sender | SES | Sends properly formatted emails; sandbox's verified-recipient limit fits one user | SNS email (plain notification text) |

### Supporting Services

| Purpose | Service | Why |
|---------|---------|-----|
| Infrastructure as code | CDK (Python) | Redeploy the full stack with one command; doubles as Python practice |
| Monitoring | CloudWatch | Logs for every component, plus an alarm that emails me if the 2am run fails |
| Cost guardrails | AWS Budgets + Cost Anomaly Detection | Alerts before costs get out of hand (alerts warn; they don't stop usage) |


## Step 5: Architecture Diagram

![Playbook v1 architecture](Playbook%20v1%20-%20Design%20Diagram.drawio.png)

The editable source is in `Playbook_v1_-_Design_Diagram.drawio`.

**Legend:** blue = user requests, orange = 2am planning, green = 5pm reminders, dashed = one-time setup.
