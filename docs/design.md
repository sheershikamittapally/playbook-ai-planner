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
