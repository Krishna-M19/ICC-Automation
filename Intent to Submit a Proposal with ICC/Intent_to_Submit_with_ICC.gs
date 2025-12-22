/**
 * Gmail to Google Sheets Automation for MTU Proposals with ICC
 */

// Configuration
const SHEET_ID = ''; //Intent to Submit With ICC Spreadsheet id
const SHEET_NAME = 'Intent to Submit with ICC';

// Questions that appear in emails
const QUESTIONS = [
    'Email address',
    'Sponsor',
    'Michigan Tech Point of Contact / Principal Investigator',
    'Is Michigan Tech the lead organization?',
    'Official Sponsor Deadline (leave blank for flexible deadlines)',
    'Lead organization deadline (leave blank if Michigan Tech is the lead organization)',
    'Expected Submission Date',
    'Total estimated budget',
    'Additional Comments',
    'Solicitation, CFP, FOA, BAA, etc. (if available)',
    'Co-investigators',
    "Is this the PI's first proposal to this sponsor?",
    'Will any of the sponsored funds be used for payment to individuals or organizations outside of Michigan Tech (e.g. sub-recipients, service providers/vendors, or consultants)?',
    'Will there be Foundation or Industry Involvement (either funded or unfunded)?',
    'Will there be any human subjects in this project?',
    'Will there be any animal subjects in this project?',
    'Will there be any biological agents in this project?',
    'Is there a limit to the number of proposals submitted by an institution?',
    'Are you planning on submitting this proposal through a research institute?',
    'Are you planning on incorporating a Michigan Tech shared facility in this proposal?'
];

/**
 * Main function to process proposal emails
 */
function processProposalEmails() {
    try {
        console.log('Starting proposal email processing...');

        // Get emails from newproposal@mtu.edu
        const threads = GmailApp.search(`from:newproposal@mtu.edu subject:"New response to Intent to Submit a New Proposal"`);

        if (threads.length === 0) {
            console.log('No proposal emails found');
            return;
        }

        console.log(`Found ${threads.length} email threads`);
        const sheet = getOrCreateSheet();

        // Get existing processed threads to avoid duplicates
        const processedThreads = getProcessedThreads(sheet);
        let processedCount = 0;
        let skippedCount = 0;

        threads.forEach((thread, index) => {
            const threadId = thread.getId();

            // Skip if already processed
            if (processedThreads.has(threadId)) {
                skippedCount++;
                return;
            }

            // Get the first message from newproposal@mtu.edu (original message)
            const originalMessage = getOriginalMessage(thread);

            if (originalMessage) {
                const proposalData = extractProposalData(originalMessage, threadId);
                if (proposalData.principalInvestigator) {
                    addToSheet(sheet, proposalData);
                    processedCount++;
                    console.log(`${processedCount}. Processed: ${proposalData.principalInvestigator}`);
                }
            }
        });

        console.log(`\n Complete! Processed: ${processedCount}, Skipped: ${skippedCount}`);

    } catch (error) {
        console.error('Error:', error);
    }
}

/**
 * Get the original message from newproposal@mtu.edu (not replies)
 */
function getOriginalMessage(thread) {
    const messages = thread.getMessages();

    for (const message of messages) {
        const from = message.getFrom();
        const subject = message.getSubject();

        if (from.includes('newproposal@mtu.edu') &&
            subject.includes('New response to "Intent to Submit a New Proposal"')) {
            return message;
        }
    }

    return null;
}

/**
 * Get list of already processed thread IDs
 */
function getProcessedThreads(sheet) {
    const processedThreads = new Set();

    if (sheet.getLastRow() > 1) {
                // Find Thread ID column by header name
        const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
        const threadIdColumn = headers.indexOf('Thread ID') + 1;
        
        if (threadIdColumn > 0) {
            const threadIds = sheet.getRange(2, threadIdColumn, sheet.getLastRow() - 1, 1).getValues();
            threadIds.forEach(row => {
                if (row[0]) {
                    processedThreads.add(row[0]);
                }
            });
        }
    }

    return processedThreads;
}

/**
 * Extract proposal data using pattern matching
 */
function extractProposalData(message, threadId) {
    const body = message.getPlainBody();
    const subject = message.getSubject();
    const date = message.getDate();

    // Extract PI name from subject
    const piMatch = subject.match(/from (.+)$/);
    const principalInvestigator = piMatch ? piMatch[1] : '';

    // Extract answers for each question
    const answers = {};

    QUESTIONS.forEach(question => {
        const answer = extractAnswer(body, question);
        answers[question] = answer;



    });

    return {
        date: formatDate(date),
        principalInvestigator: principalInvestigator,
        answers: answers,
        threadId: threadId
    };
}

/**
 * Extract answer for a specific question - handles collapsed whitespace in email body
 */
function extractAnswer(body, question) {
    // Normalize whitespace in both body and question for flexible matching
    const normalizedBody = body.replace(/\s+/g, ' ').trim();
    const normalizedQuestion = question.replace(/\s+/g, ' ').trim();

    // Find the question in the normalized body (case-insensitive)
    const lowerBody = normalizedBody.toLowerCase();
    const lowerQuestion = normalizedQuestion.toLowerCase();
    const questionIndex = lowerBody.indexOf(lowerQuestion);

    if (questionIndex === -1) {
        return ''; // Question not found
    }

    // Get everything after the question
    const afterQuestion = normalizedBody.substring(questionIndex + normalizedQuestion.length).trim();

    // Remove leading "?" if present
    const cleanAfter = afterQuestion.replace(/^\?\s*/, '');

    // Find where the next question starts
    let nextQuestionIndex = cleanAfter.length;

    for (const q of QUESTIONS) {
        const normalizedQ = q.replace(/\s+/g, ' ').trim();
        const lowerQ = normalizedQ.toLowerCase();
        const idx = cleanAfter.toLowerCase().indexOf(lowerQ);

        // Only consider it a new question if it's found and not at position 0
        if (idx > 0 && idx < nextQuestionIndex) {
            nextQuestionIndex = idx;
        }
    }

    // Extract the answer (everything between this question and the next)
    let answer = cleanAfter.substring(0, nextQuestionIndex).trim();

    return answer;
}

/**
 * Format date as YYYY-MM-DD
 */
function formatDate(date) {
    return Utilities.formatDate(date, Session.getScriptTimeZone(), 'yyyy-MM-dd');
}

/**
 * Escape special regex characters
 */
function escapeRegex(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/**
 * Get or create the Google Sheet
 */
function getOrCreateSheet() {
    const spreadsheet = SpreadsheetApp.openById(SHEET_ID);
    let sheet = spreadsheet.getSheetByName(SHEET_NAME);

    if (!sheet) {
        sheet = spreadsheet.insertSheet(SHEET_NAME);
        setupHeaders(sheet);
    }

    if (sheet.getLastRow() === 0) {
        setupHeaders(sheet);
    }

    return sheet;
}

/**
 * Setup column headers
 */
function setupHeaders(sheet) {
    const headers = [
        'Date',
        'Principal Investigator (from subject)',
        ...QUESTIONS, // All the questions as column headers
        'Thread ID', // For duplicate prevention
        'Spreadsheet Created' // Checkbox to track if task template was created
    ];

    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    sheet.getRange(1, 1, 1, headers.length).setFontWeight('bold');
    sheet.setFrozenRows(1);
    
    // Note: Checkbox validation will be applied to each row as data is added in addToSheet()
}

/**
 * Add data to sheet
 */
function addToSheet(sheet, data) {
    const row = [
        data.date,
        data.principalInvestigator
    ];

    // Add answers for each question in order
    QUESTIONS.forEach(question => {
        row.push(data.answers[question] || '');
    });

    // Add thread ID for duplicate prevention
    row.push(data.threadId);

    // Add Spreadsheet Created checkbox (initially unchecked)
    row.push(false);

    const newRowNumber = sheet.getLastRow() + 1;
    sheet.appendRow(row);

    // Apply checkbox validation to the new row's last column
    const checkboxColumn = row.length;
    const checkboxRule = SpreadsheetApp.newDataValidation()
        .requireCheckbox()
        .setAllowInvalid(false)
        .build();
    sheet.getRange(newRowNumber, checkboxColumn).setDataValidation(checkboxRule);
}

/**
 * Setup automatic trigger
 */
function setupTrigger() {
    // Delete existing triggers
    const triggers = ScriptApp.getProjectTriggers();
    triggers.forEach(trigger => {
        if (trigger.getHandlerFunction() === 'processProposalEmails') {
            ScriptApp.deleteTrigger(trigger);
        }
    });

    // Create new trigger every 6 hours
    ScriptApp.newTrigger('processProposalEmails')
        .timeBased()
        .everyHours(6)
        .create();

    console.log('Trigger setup - will run every 6 hours');
}

/**
 * Initial setup
 */
function initialSetup() {
    setupTrigger();
    console.log('Setup complete! Run processProposalEmails() to start.');
}

/**
 * Clear sheet data (keep headers) - useful for reprocessing
 */
function clearSheetData() {
    const sheet = getOrCreateSheet();
    if (sheet.getLastRow() > 1) {
        sheet.getRange(2, 1, sheet.getLastRow() - 1, sheet.getLastColumn()).clear();
        console.log('Sheet cleared. Headers remain. Run processProposalEmails() to reprocess.');
    } else {
        console.log('Sheet is already empty.');
    }
}
