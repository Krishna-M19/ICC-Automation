# Intent to Submit a Proposal with ICC - Email to Sheets Automation

## Overview

This Google Apps Script automates the process of extracting "Intent to Submit a New Proposal" responses from Gmail and organizing them into a Google Sheet for tracking and coordination.

## Background

When a Principal Investigator (PI) submits an Intent to Submit form, the ICC does not have direct access to the form response spreadsheet. Instead, ICC receives the information via email from `newproposals@mtu.edu` when a PI expresses interest in submitting a proposal with ICC support.

Since email format is difficult to track and manage, this script automatically:
- Retrieves form responses from emails with a subject "New response to "Intent to Submit a New Proposal" from " sent by `newproposal@mtu.edu`
- Extracts all question-answer pairs from the email body
- Organizes the data into a structured Google Sheet
- Prevents duplicate entries using thread ID tracking

## Purpose

The "Notice of Intent to Submit a Proposal" form gathers minimal key information to coordinate support for proposals. This automation ensures that all intent submissions are captured systematically for better planning and tracking.

## Features

- **Automatic Email Processing**: Searches for emails from `ewproposal@mtu.edu` with subject "New response to Intent to Submit a New Proposal"
- **Data Extraction**: Extracts key fields
- **Duplicate Prevention**: Tracks processed emails using thread IDs
- **Automated Scheduling**: Runs every 0.5 hours via time-based trigger
- **Spreadsheet Tracking**: Includes a checkbox column to track if task templates have been created

## Configuration

Update these constants at the top of the script:

```javascript
const SHEET_ID = ''; //Intent to Submit with ICC spreadsheet
const SHEET_NAME = 'Intent to Submit with ICC';
```

## Setup Instructions

1. **Open Google Apps Script**:
   - Go to [script.google.com](https://script.google.com)
   - Create a new project
   - Paste the code from `Intent_to_submit_with_ICC.gs`

2. **Configure Sheet ID**:
   - Update `SHEET_ID` with your Google Sheet ID
   - The sheet will be created automatically if it doesn't exist

3. **Authorize Gmail Access**:
   - Run `processProposalEmails()` manually once
   - Grant necessary permissions when prompted

4. **Setup Automatic Trigger**:
   - This creates a time-based trigger to run every 0.5 hours

## Functions

### Main Functions

- `processProposalEmails()` - Main function that processes all unprocessed emails
- `setupTrigger()` - Creates/updates the time-based trigger

### Utility Functions

- `getOriginalMessage(thread)` - Extracts the original form response email
- `extractProposalData(message, threadId)` - Parses email content into structured data
- `extractAnswer(body, question)` - Extracts specific answers using pattern matching
- `getProcessedThreads(sheet)` - Retrieves list of already processed emails
- `addToSheet(sheet, data)` - Adds new proposal data to the sheet
- `clearSheetData()` - Clears all data except headers (useful for reprocessing)

## Sheet Structure

The Google Sheet includes the following columns:

1. Date
2. Principal Investigator (extracted from email subject)
3. Email address
4. Sponsor
5. Michigan Tech Point of Contact / Principal Investigator
6. Is Michigan Tech the lead organization?
7. Official Sponsor Deadline
8. Lead organization deadline
9. Expected Submission Date
10. Total estimated budget
11. Additional Comments
12. Solicitation, CFP, FOA, BAA, etc.
13. Co-investigators
14. Is this the PI's first proposal to this sponsor?
15. Will any sponsored funds be used for external payments?
16. Will there be Foundation or Industry Involvement?
17. Will there be any human subjects?
18. Will there be any animal subjects?
19. Will there be any biological agents?
20. Is there a limit to the number of proposals?
21. Are you planning on submitting through a research institute?
22. Are you planning on incorporating a Michigan Tech shared facility?
23. Thread ID (for duplicate prevention)
24. Spreadsheet Created (checkbox for tracking)


## Notes

- The script processes only when new email pops.
- Thread IDs are used to prevent duplicate entries.
- The "Spreadsheet Created" checkbox can be used to track ICC task template/checklist creation.
