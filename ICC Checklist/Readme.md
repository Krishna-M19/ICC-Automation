# ICC Proposal Task Template/Checklist Generator

## Overview

This automation project creates customized task tracking spreadsheets for each PI to manage their proposal submission process efficiently.

### What It Does

The system automatically:
- Reads proposal information from the "Intent to Submit with ICC" Google Spreadsheet
- Creates individual task template spreadsheets for each PI
- Calculates deadlines for task schedules based on university holidays
- Maintains synchronized holiday calendars across all generated spreadsheets

## Key Features

### Deadline Management

The system uses an formulated deadline calculation:
- Integrates with Google Calendar to fetch federal holidays
- We should manually add and maintain university holidays list in the source spreadsheet, so that it will reflect in all newly created task template sheets.
- Uses the `WORKDAY()` formula to calculate business days, automatically excluding holidays
- Copies the holidays sheet from source spreadsheet to each task template for accurate deadline calculations
- Prioritizes deadlines in this order: Lead Organization Deadline → Official Sponsor Deadline → Expected Submission Date

### Automated Task Templates

Each generated spreadsheet includes:
- **Task Checklist Sheet**: Multiple proposal preparation tasks for Full Budget Draft, Tier 1 tasks and Tier 2 tasks.
- **Personnel Docs Sheet**: Tasks for PI and up to 5 Co-PIs
- **Holidays Sheet**: University and federal holidays for deadline calculations retrieved from source spreadsheet.

### Synchronization

The system can update holiday information across all existing spreadsheets when holidays change/updated manually in Source Spreadsheet (Intent to submit with ICC - "holiday" sheet), ensuring deadline accuracy throughout the proposal lifecycle.

## Project Structure

### Core Files

#### `Config.gs`
Configuration constants for the entire project:
- `SOURCE_SHEET_ID`: The Google Spreadsheet containing "Intent to Submit with ICC" data
- `SOURCE_SHEET_NAME`: The sheet name within the source spreadsheet
- `DESTINATION_FOLDER_ID`: Google Drive folder where task templates are created

#### `Main.gs`
Entry point functions:
- `runAll()`: Creates new spreadsheets AND updates holidays in all existing spreadsheets

#### `ProposalManager.gs`
Handles proposal data extraction and spreadsheet creation:
- `getProposals()`: Reads proposal data from the source sheet
- `createProposalSpreadsheet()`: Creates a new task template spreadsheet
- `getPriorityDeadline()`: Determines which deadline to use for naming and calculations
- `markSpreadsheetAsCreated()`: Updates the source sheet by checking the box to prevent duplication

#### `HolidayManager.gs`
Manages holiday synchronization:
- `syncHolidaysFromCalendar()`: Fetches federal holidays from Google Calendar (3-year range)
- `ensureSourceHolidaysSheet()`: Creates or verifies the Holidays sheet in the source spreadsheet
- `getHolidayDataFromSource()`: Retrieves holiday data for copying to new spreadsheets
- `updateHolidaysInExistingSpreadsheets()`: Updates holidays across all task templates (only if changed)
- `calculateHolidayHash()`: Detects changes in holiday data to avoid unnecessary updates

#### `TemplateBuilder.gs`
Builds the structure and content of task template spreadsheets:
- `buildProposalTemplate()`: Creates the Task Checklist sheet with proposal information and tasks
- `buildPersonnelDocsSheet()`: Creates the Personnel Docs sheet for tracking PI/Co-PI tasks
- `applyStatusColors()`: Applies conditional formatting for task status visualization

#### `TaskSections.gs`
Helper functions for adding task sections:
- `addSection()`: Adds a task section with deadline calculations
- `addSectionWithNotes()`: Adds a task section with notes/links for each task
- `addPersonnelSection()`: Adds personnel-specific document tracking sections

## How It Works

### Workflow

1. **Data Collection**: PIs fill out the "Intent to Submit with ICC" form, which populates the source spreadsheet
2. **Holiday Sync**: The system fetches federal holidays from Google Calendar and maintains them in the source spreadsheet
3. **Spreadsheet Generation**: For each proposal without a spreadsheet:
   - Creates a new Google Spreadsheet named: `[PI Name] - [Sponsor] - [Deadline]`
   - Copies proposal details and Co-Investigator information from source
   - Generates task sections with calculated deadlines
   - Copies the holidays sheet for deadline calculations
4. **Deadline Calculation**: Each task has a deadline calculated using the `WORKDAY()` formula:
   ```
   =TEXT(WORKDAY([Reference Deadline], -[Business Days], Holidays!$A$2:$A), "MM/DD/YYYY")
   ```
   
   **WORKDAY Formula:**
   ```
   WORKDAY(start_date, -num_days, [holidays])
   ```
   
   Calculates working days backwards from the official sponsor deadline.
   
   - **start_date**: The official sponsor deadline
   - **-num_days**: Number of working days to count backwards
   - **[holidays]**: Holiday dates from the Holidays sheet
   
   U.S. Holiday Calendar: https://calendar.google.com/calendar/embed?src=en.usa%23holiday%40group.v.calendar.google.com&ctz=America%2FNew_York
   
   **Example:**
   
   Official Sponsor Deadline (D): 10/30/2025
   - Formula for Tier 2 deadline: `TEXT(WORKDAY(D, -1, [holidays]), "MM/DD/YYYY")` = 10/29/2025
   - Formula for Tier 1 deadline: `TEXT(WORKDAY(C, -4, [holidays]), "MM/DD/YYYY")` = 10/23/2025
   - Formula for Full Budget Draft: `TEXT(WORKDAY(B, -5, [holidays]), "MM/DD/YYYY")` = 10/16/2025
   
   Where:
   - D = Official Sponsor deadline
   - C = Tier 2 tasks
   - B = Tier 1 tasks
   - A = Full budget draft

5. **Status Tracking**: Tasks include dropdown status options with color coding:
   - Not Started (Red)
   - In Progress (Yellow)
   - Completed (Green)
   - Not Applicable (Gray)

### Task Organization
Tasks are organized into three tiers:

- **Full Budget Draft** (5 business days before Tier 1): Budget drafts, Cayuse setup, subrecipient paperwork
- **Tier 1: Internal and Non-Science Documents** (4 business days before Tier 2): Budget justification, data management plan, facilities documentation
- **Tier 2: Science Related and Technical Documents** (1 business day before official deadline): Project summary, description, research strategy

## Setup Instructions

### Prerequisites

- Google Account with access to Google Apps Script
- Source spreadsheet with "Intent to Submit with ICC" data
- Google Drive folder for storing generated spreadsheets
- Access to Google Calendar API

### Configuration

1. Open Google Apps Script editor
3. Update `Config.gs` with your IDs:
   ```javascript
   const SOURCE_SHEET_ID = 'Intent to Submit With ICC Spreadsheet id';
   const SOURCE_SHEET_NAME = 'Intent to Submit with ICC';
   const DESTINATION_FOLDER_ID = 'Destination Drive/Folder ID';
   ```


## Usage

### Automated Execution

The application runs every 1 hour via time-driven trigger to:
- Check for new proposals in the source spreadsheet
- Create task spreadsheets for new proposals
- Update holidays in existing spreadsheets (only if changed)

Manual Execution - You can also manually run `runAll()` from the Apps Script editor to:

## Technical Notes

- Built with Google Apps Script (JavaScript-based)
- Uses Google Sheets API for spreadsheet manipulation
- Integrates with Google Calendar API for holiday data
- Implements MD5 hashing for efficient change detection
- Uses conditional formatting for visual status tracking

## License

This project is maintained by the Institute of Computing and Cybersystems at Michigan Tech.

---
