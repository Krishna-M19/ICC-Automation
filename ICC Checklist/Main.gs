/**
 * Main function - creates new spreadsheets AND updates holidays in existing ones
 */
function runAll() {
    const sourceSpreadsheet = SpreadsheetApp.openById(SOURCE_SHEET_ID);
    const sourceSheet = sourceSpreadsheet.getSheetByName(SOURCE_SHEET_NAME);
    const proposals = getProposals(sourceSheet);

    ensureSourceHolidaysSheet(sourceSpreadsheet);
    const holidayData = getHolidayDataFromSource(sourceSpreadsheet);

    const folder = DESTINATION_FOLDER_ID ?
        DriveApp.getFolderById(DESTINATION_FOLDER_ID) :
        DriveApp.getRootFolder();

    proposals.forEach(proposal => {
        createProposalSpreadsheet(proposal, folder, holidayData);
    });

    console.log(`Created ${proposals.length} new spreadsheets`);

    updateHolidaysInExistingSpreadsheets();
    
    console.log('All done!');
}
