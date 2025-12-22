/**
 * Proposal Management
 * Handles reading proposals and creating spreadsheets
 */

/**
 * Get proposals from source sheet
 */
function getProposals(sheet) {
    const data = sheet.getDataRange().getValues();
    const headers = data[0];
    const proposals = [];

    for (let i = 1; i < data.length; i++) {
        const row = data[i];
        const pi = row[headers.indexOf('Principal Investigator (from subject)')];
        const email = row[headers.indexOf('Email address')];
        const sponsor = row[headers.indexOf('Sponsor')];
        const coInvestigators = row[headers.indexOf('Co-investigators')] || '';
        const deadline = row[headers.indexOf('Official Sponsor Deadline (leave blank for flexible deadlines)')] || '';
        const leadOrgDeadline = row[headers.indexOf('Lead Organization Deadline')] || '';
        const expectedSubmission = row[headers.indexOf('Expected Submission Date')] || '';
        const spreadsheetCreated = row[headers.indexOf('Spreadsheet Created')] || false;

        if (pi && (deadline || leadOrgDeadline || expectedSubmission) && !spreadsheetCreated) {
            proposals.push({
                pi,
                email,
                sponsor,
                coInvestigators,
                deadline,
                leadOrgDeadline,
                expectedSubmission,
                rowIndex: i + 1
            });
        }
    }

    return proposals;
}

/**
 * Get priority deadline for naming (Lead Org > Official > Expected)
 */
function getPriorityDeadline(proposal) {
    // Priority: Lead Org Deadline > Official Deadline > Expected Submission
    if (proposal.leadOrgDeadline) {
        return proposal.leadOrgDeadline;
    } else if (proposal.deadline) {
        return proposal.deadline;
    } else if (proposal.expectedSubmission) {
        return proposal.expectedSubmission;
    }
    return null;
}

/**
 * Format date as MM-DD-YYYY
 */
function formatDateForFilename(dateValue) {
    if (!dateValue) return '';
    
    const date = new Date(dateValue);
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const year = date.getFullYear();
    
    return `${month}-${day}-${year}`;
}

/**
 * Create a new spreadsheet for one proposal
 */
function createProposalSpreadsheet(proposal, folder, holidayData) {
    const sanitizedPI = proposal.pi.substring(0, 50).replace(/[\/\\\?\*\[\]]/g, '_');
    const sanitizedSponsor = proposal.sponsor.substring(0, 50).replace(/[\/\\\?\*\[\]]/g, '_');
    
    // Get priority deadline and format it
    const priorityDeadline = getPriorityDeadline(proposal);
    const deadlineStr = formatDateForFilename(priorityDeadline);
    
    // Build spreadsheet name with deadline
    const spreadsheetName = deadlineStr ? 
        `${sanitizedPI} - ${sanitizedSponsor} - ${deadlineStr}` :
        `${sanitizedPI} - ${sanitizedSponsor}`;

    const existingFiles = folder.getFilesByName(spreadsheetName);
    if (existingFiles.hasNext()) {
        console.log(`Spreadsheet "${spreadsheetName}" already exists - skipping`);
        return;
    }

    const newSpreadsheet = SpreadsheetApp.create(spreadsheetName);
    const spreadsheetFile = DriveApp.getFileById(newSpreadsheet.getId());

    if (DESTINATION_FOLDER_ID) {
        spreadsheetFile.moveTo(folder);
    }

    const taskSheet = newSpreadsheet.getSheets()[0];
    taskSheet.setName('Task Checklist');

    const personnelSheet = newSpreadsheet.insertSheet('Personnel Docs', 1);
    const holidaySheet = newSpreadsheet.insertSheet('Holidays', 2);

    if (holidayData && holidayData.length > 0) {
        holidaySheet.getRange(1, 1, holidayData.length, 2).setValues(holidayData);
        holidaySheet.getRange(1, 1, 1, 2).setFontWeight('bold');
    }

    buildProposalTemplate(taskSheet, proposal, 1);

    taskSheet.setColumnWidth(1, 400);
    taskSheet.setColumnWidth(2, 150);
    taskSheet.setColumnWidth(3, 120);
    taskSheet.setColumnWidth(4, 400);
    taskSheet.setFrozenRows(6);

    buildPersonnelDocsSheet(personnelSheet, proposal);
    personnelSheet.setFrozenRows(6);

    // Share spreadsheet with editor
    // shareSpreadsheetWithEditor(newSpreadsheet);

    console.log(`Created spreadsheet: ${spreadsheetName}`);

    markSpreadsheetAsCreated(proposal.rowIndex);
}

// /**
//  * Share spreadsheet with configured editor emails
//  */
// function shareSpreadsheetWithEditor(spreadsheet) {
//   EDITOR_EMAILS.forEach(email => {
//     spreadsheet.addEditor(email);
//     console.log(`Shared with ${email} as editor`);
//   });
// }

/**
 * Mark a proposal as having its spreadsheet created
 */
function markSpreadsheetAsCreated(rowIndex) {
    try {
        const sourceSpreadsheet = SpreadsheetApp.openById(SOURCE_SHEET_ID);
        const sourceSheet = sourceSpreadsheet.getSheetByName(SOURCE_SHEET_NAME);
        const headers = sourceSheet.getRange(1, 1, 1, sourceSheet.getLastColumn()).getValues()[0];
        const checkboxColumn = headers.indexOf('Spreadsheet Created') + 1;

        if (checkboxColumn > 0) {
            sourceSheet.getRange(rowIndex, checkboxColumn).setValue(true);
        }
    } catch (error) {
        console.error(`Error marking row ${rowIndex} as created: ${error}`);
    }
}
