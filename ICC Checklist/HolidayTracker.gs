/**
 * Holiday Tracker
 * Ensure Holidays sheet exists in source spreadsheet via syncing and updating
 */

function ensureSourceHolidaysSheet(sourceSpreadsheet) {
    let holidaySheet = sourceSpreadsheet.getSheetByName('Holidays');

    if (!holidaySheet) {
        holidaySheet = sourceSpreadsheet.insertSheet('Holidays');
        console.log('Created Holidays sheet in source spreadsheet');

        const holidays = syncHolidaysFromCalendar();

        if (holidays.length === 0) {
            console.warn('No holidays found in calendar. Using empty holiday list.');
            holidaySheet.getRange(1, 1, 1, 2).setValues([['Holiday Date', 'Holiday Name']]);
            holidaySheet.getRange(1, 1, 1, 2).setFontWeight('bold');
        } else {
            holidaySheet.getRange(1, 1, 1, 2).setValues([['Holiday Date', 'Holiday Name']]);
            holidaySheet.getRange(2, 1, holidays.length, 2).setValues(holidays);
            holidaySheet.getRange(1, 1, 1, 2).setFontWeight('bold');
            console.log(`Synced ${holidays.length} holidays to source spreadsheet`);
        }
    } else {
        console.log('Holidays sheet already exists in source spreadsheet');
    }
}

/**
 * Get holiday data from source spreadsheet
 */
function getHolidayDataFromSource(sourceSpreadsheet) {
    const holidaySheet = sourceSpreadsheet.getSheetByName('Holidays');
    if (!holidaySheet) {
        console.error('Holidays sheet not found in source spreadsheet');
        return [['Holiday Date', 'Holiday Name']];
    }

    const lastRow = holidaySheet.getLastRow();
    if (lastRow < 1) {
        return [['Holiday Date', 'Holiday Name']];
    }

    return holidaySheet.getRange(1, 1, lastRow, 2).getValues();
}

/**
 * Sync holidays from Google Calendar (3 years)
 */
function syncHolidaysFromCalendar() {
    try {
        const HOLIDAY_CALENDAR_ID = 'en.usa#holiday@group.v.calendar.google.com';
        const calendar = CalendarApp.getCalendarById(HOLIDAY_CALENDAR_ID);

        if (!calendar) {
            console.error('Holiday calendar not found.');
            return [];
        }

        const currentYear = new Date().getFullYear();
        const startDate = new Date(currentYear, 0, 1);
        const endDate = new Date(currentYear + 3, 0, 1);

        const events = calendar.getEvents(startDate, endDate);
        const holidays = [];
        const seenDates = new Set();

        const observancePatterns = [
            'eve', 'observed', 'observance', 'daylight saving', 'groundhog',
            'valentine', 'st. patrick', 'april fools', 'earth day', 'cinco de mayo',
            'mother\'s day', 'father\'s day', 'halloween', 'election day',
            'pearl harbor', 'flag day', 'patriots\' day', 'tax day'
        ];

        const federalHolidays = [
            'new year', 'martin luther king', 'mlk', 'presidents', 'president\'s day',
            'memorial day', 'juneteenth', 'independence day', 'labor day',
            'columbus day', 'indigenous peoples', 'veterans day', 'thanksgiving', 'christmas'
        ];

        events.forEach(event => {
            const eventTitle = event.getTitle().toLowerCase();
            const eventDate = event.getAllDayStartDate();
            const dateStr = Utilities.formatDate(eventDate, Session.getScriptTimeZone(), 'yyyy-MM-dd');

            if (seenDates.has(dateStr)) return;

            const isFederalHoliday = federalHolidays.some(holiday => eventTitle.includes(holiday));
            if (!isFederalHoliday) return;

            const isObservance = observancePatterns.some(pattern => eventTitle.includes(pattern));
            if (isObservance) return;

            seenDates.add(dateStr);
            holidays.push([dateStr, event.getTitle()]);
        });

        holidays.sort((a, b) => a[0].localeCompare(b[0]));
        return holidays;

    } catch (error) {
        console.error('Error syncing holidays:', error);
        return [];
    }
}

/**
 * Calculate hash of holiday data for change detection
 */
function calculateHolidayHash(holidayData) {
    const dataString = JSON.stringify(holidayData);
    const rawHash = Utilities.computeDigest(Utilities.DigestAlgorithm.MD5, dataString);
    
    const hashString = rawHash.map(byte => {
        const hex = (byte < 0 ? byte + 256 : byte).toString(16);
        return hex.length === 1 ? '0' + hex : hex;
    }).join('');
    
    return hashString;
}

/**
 * Update Holidays tab in all existing spreadsheets (only if data changed)
 */
function updateHolidaysInExistingSpreadsheets() {
    const sourceSpreadsheet = SpreadsheetApp.openById(SOURCE_SHEET_ID);
    const holidayData = getHolidayDataFromSource(sourceSpreadsheet);

    if (!holidayData || holidayData.length === 0) {
        console.error('No holiday data found in source spreadsheet');
        return;
    }

    const sourceHash = calculateHolidayHash(holidayData);

    const folder = DESTINATION_FOLDER_ID ?
        DriveApp.getFolderById(DESTINATION_FOLDER_ID) :
        DriveApp.getRootFolder();

    const files = folder.getFiles();
    let updatedCount = 0;
    let skippedCount = 0;

    while (files.hasNext()) {
        const file = files.next();

        if (file.getId() === SOURCE_SHEET_ID) {
            continue;
        }

        if (file.getMimeType() === MimeType.GOOGLE_SHEETS) {
            try {
                const spreadsheet = SpreadsheetApp.openById(file.getId());
                const holidaySheet = spreadsheet.getSheetByName('Holidays');

                if (holidaySheet) {
                    const lastRow = holidaySheet.getLastRow();
                    const existingData = lastRow > 0 ?
                        holidaySheet.getRange(1, 1, lastRow, 2).getValues() :
                        [];

                    const existingHash = calculateHolidayHash(existingData);

                    if (existingHash !== sourceHash) {
                        holidaySheet.clear();
                        holidaySheet.getRange(1, 1, holidayData.length, 2).setValues(holidayData);
                        holidaySheet.getRange(1, 1, 1, 2).setFontWeight('bold');

                        console.log(`Updated holidays in: ${file.getName()}`);
                        updatedCount++;
                    } else {
                        console.log(`Skipped (no changes): ${file.getName()}`);
                        skippedCount++;
                    }
                }
            } catch (error) {
                console.error(`Error updating ${file.getName()}: ${error}`);
            }
        }
    }

    console.log(`Updated: ${updatedCount} spreadsheets, Skipped: ${skippedCount} spreadsheets (no changes)`);
}
