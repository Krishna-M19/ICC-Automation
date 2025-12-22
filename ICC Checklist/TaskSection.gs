/**
 * Section
 * Functions for adding sections and tasks to sheets
 */

/**
 * Add a section with tasks and optional notes
 */
function addSectionWithNotes(sheet, startRow, sectionTitle, tasksWithNotes, businessDaysBefore, deadlineCell) {
    const deadlineFormula = `=TEXT(WORKDAY(${deadlineCell}, -${businessDaysBefore}, Holidays!$A$2:$A), "MM/DD/YYYY")`;
    sheet.getRange(startRow, 1).setValue(sectionTitle);
    sheet.getRange(startRow, 3).setFormula(deadlineFormula);

    sheet.getRange(startRow, 1, 1, 3)
        .setFontWeight('bold')
        .setBackground('#d9d9d9');

    const sectionHeaderRow = startRow;
    startRow++;

    const firstTaskRow = startRow;

    const taskNames = Object.keys(tasksWithNotes);
    taskNames.forEach(task => {
        sheet.getRange(startRow, 1).setValue(task);

        const statusRule = SpreadsheetApp.newDataValidation()
            .requireValueInList(['Not Started', 'In Progress', 'Completed', 'Not Applicable'], true)
            .setAllowInvalid(false)
            .build();
        const statusCell = sheet.getRange(startRow, 2);
        statusCell.setDataValidation(statusRule);
        statusCell.setValue('Not Started');

        sheet.getRange(startRow, 3).setFormula(`=C${sectionHeaderRow}`);
        sheet.getRange(startRow, 3).setNumberFormat('MM/dd/yyyy');

        const note = tasksWithNotes[task];
        if (note) {
            sheet.getRange(startRow, 4).setValue(note);
        }

        startRow++;
    });

    const lastTaskRow = startRow - 1;
    if (lastTaskRow >= firstTaskRow) {
        sheet.getRange(firstTaskRow, 1, lastTaskRow - firstTaskRow + 1, 1).shiftRowGroupDepth(1);
    }

    startRow++;
    return startRow;
}

/**
 * Add a section with tasks
 */
function addSection(sheet, startRow, sectionTitle, tasks, businessDaysBefore, deadlineCell) {
    const deadlineFormula = `=TEXT(WORKDAY(${deadlineCell}, -${businessDaysBefore}, Holidays!$A$2:$A), "MM/DD/YYYY")`;
    sheet.getRange(startRow, 1).setValue(sectionTitle);
    sheet.getRange(startRow, 3).setFormula(deadlineFormula);

    sheet.getRange(startRow, 1, 1, 3)
        .setFontWeight('bold')
        .setBackground('#d9d9d9');

    const sectionHeaderRow = startRow;
    startRow++;

    const firstTaskRow = startRow;

    let subrecipientStartRow = null;
    let inSubrecipientGroup = false;

    tasks.forEach((task, index) => {
        sheet.getRange(startRow, 1).setValue(task);

        if (task.includes('Subrecipient Paperwork')) {
            sheet.getRange(startRow, 1).setFontWeight('bold');
            subrecipientStartRow = startRow + 1;
            inSubrecipientGroup = true;
        } else {
            const statusRule = SpreadsheetApp.newDataValidation()
                .requireValueInList(['Not Started', 'In Progress', 'Completed', 'Not Applicable'], true)
                .setAllowInvalid(false)
                .build();
            const statusCell = sheet.getRange(startRow, 2);
            statusCell.setDataValidation(statusRule);
            statusCell.setValue('Not Started');

            sheet.getRange(startRow, 3).setFormula(`=C${sectionHeaderRow}`);
            sheet.getRange(startRow, 3).setNumberFormat('MM/dd/yyyy');
        }

        if (inSubrecipientGroup && index < tasks.length - 1) {
            const nextTask = tasks[index + 1];
            if (!nextTask.startsWith('  ')) {
                if (subrecipientStartRow && startRow >= subrecipientStartRow) {
                    const group = sheet.getRowGroup(subrecipientStartRow, 1);
                    if (!group) {
                        sheet.getRange(subrecipientStartRow, 1, startRow - subrecipientStartRow + 1, 1).shiftRowGroupDepth(1);
                    }
                }
                inSubrecipientGroup = false;
                subrecipientStartRow = null;
            }
        }

        startRow++;
    });

    if (inSubrecipientGroup && subrecipientStartRow) {
        sheet.getRange(subrecipientStartRow, 1, startRow - subrecipientStartRow, 1).shiftRowGroupDepth(1);
    }

    const lastTaskRow = startRow - 1;
    if (lastTaskRow >= firstTaskRow) {
        sheet.getRange(firstTaskRow, 1, lastTaskRow - firstTaskRow + 1, 1).shiftRowGroupDepth(1);
    }

    startRow++;
    return startRow;
}

/**
 * Add a personnel section (PI or Co-PI) with tasks and Notes
 */
function addPersonnelSection(sheet, startRow, label, tasksWithNotes, officialDeadlineCell) {
    const deadlineFormula = `=TEXT(WORKDAY(${officialDeadlineCell}, -5, Holidays!$A$2:$A), "MM/DD/YYYY")`;
    sheet.getRange(startRow, 1).setValue(label);
    sheet.getRange(startRow, 3).setFormula(deadlineFormula);

    sheet.getRange(startRow, 1, 1, 3)
        .setFontWeight('bold')
        .setBackground('#d9d9d9');

    const sectionHeaderRow = startRow;
    startRow++;

    const firstTaskRow = startRow;

    const taskNames = Object.keys(tasksWithNotes);
    taskNames.forEach(task => {
        sheet.getRange(startRow, 1).setValue(task);

        const statusRule = SpreadsheetApp.newDataValidation()
            .requireValueInList(['Not Started', 'In Progress', 'Completed', 'Not Applicable'], true)
            .setAllowInvalid(false)
            .build();
        const statusCell = sheet.getRange(startRow, 2);
        statusCell.setDataValidation(statusRule);
        statusCell.setValue('Not Started');

        sheet.getRange(startRow, 3).setFormula(`=C${sectionHeaderRow}`);
        sheet.getRange(startRow, 3).setNumberFormat('MM/dd/yyyy');

        // Add note if provided
        const note = tasksWithNotes[task];
        if (note) {
            sheet.getRange(startRow, 4).setValue(note);
        }

        startRow++;
    });

    const lastTaskRow = startRow - 1;
    if (lastTaskRow >= firstTaskRow) {
        sheet.getRange(firstTaskRow, 1, lastTaskRow - firstTaskRow + 1, 1).shiftRowGroupDepth(1);
    }

    startRow++;
    return startRow;
}
