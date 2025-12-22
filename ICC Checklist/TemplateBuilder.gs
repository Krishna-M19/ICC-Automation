/**
 * Template Builder
 * Builds Task Checklist and Personnel Docs sheets
 */

function buildProposalTemplate(sheet, proposal, startRow) {
    sheet.getRange(startRow, 1).setValue(`PI: ${proposal.pi}`);
    sheet.getRange(startRow, 2).setValue('Co-PI:');
    sheet.getRange(startRow, 3, 1, 2).merge().setValue(`Sponsor: ${proposal.sponsor}`);

    sheet.getRange(startRow + 1, 1).setValue(`Email: ${proposal.email}`);
    sheet.getRange(startRow + 1, 2).setValue('Co-PI:');
    sheet.getRange(startRow + 1, 3).setValue('Official Deadline:');
    if (proposal.deadline) {
        sheet.getRange(startRow + 1, 4).setValue(new Date(proposal.deadline));
        sheet.getRange(startRow + 1, 4).setNumberFormat('MM/dd/yyyy').setHorizontalAlignment('left');
    }
    sheet.getRange(startRow + 2, 1).setValue(`Co-Investigators: ${proposal.coInvestigators || ''}`);
    sheet.getRange(startRow + 2, 2).setValue('Co-PI:');
    sheet.getRange(startRow + 2, 3).setValue('Lead Org Deadline:');
    if (proposal.leadOrgDeadline) {
        sheet.getRange(startRow + 2, 4).setValue(new Date(proposal.leadOrgDeadline));
        sheet.getRange(startRow + 2, 4).setNumberFormat('MM/dd/yyyy').setHorizontalAlignment('left');
    }

    sheet.getRange(startRow + 3, 2).setValue('Co-PI:');
    sheet.getRange(startRow + 3, 3).setValue('Expected Submission:');
    if (proposal.expectedSubmission) {
        sheet.getRange(startRow + 3, 4).setValue(new Date(proposal.expectedSubmission));
        sheet.getRange(startRow + 3, 4).setNumberFormat('MM/dd/yyyy').setHorizontalAlignment('left');
    }

    sheet.getRange(startRow + 4, 2).setValue('Co-PI:');

    sheet.getRange(startRow, 1, 5, 4)
        .setBackground('#ffd966')
        .setFontWeight('bold')
        .setFontSize(12)
        .setBorder(true, true, true, true, false, false);

    const headerRow = startRow + 5;
    sheet.getRange(headerRow, 1, 1, 4).setValues([['Task', 'Status', 'Deadline', 'Notes or Information']]);
    sheet.getRange(headerRow, 1, 1, 4)
        .setBackground('#4a86e8')
        .setFontColor('#ffffff')
        .setFontWeight('bold')
        .setBorder(true, true, true, true, true, true);

    let currentRow = headerRow + 1;
    const officialDeadlineCell = `$D${startRow + 1}`;

    const fullBudgetStartRow = currentRow;
    const tier1StartRow = fullBudgetStartRow + 21;
    const tier2StartRow = tier1StartRow + 15;

    const tier1DeadlineCell = `$C${tier1StartRow + 1}`;
    currentRow = addSection(sheet, currentRow, 'Full Budget Draft', [
        'Draft of full proposal budget',
        'Draft of Budget Justification',
        'Cayuse SOW',
        'Cayuse Number #',
        'Cayuse Abstract',
        'research.gov created and shared with AOR',
        'Subrecipient Paperwork (if applicable)',
        '  a. MTU Commitment Form',
        '  b. Scope of Work',
        '  c. Final Budget',
        '  d. Budget Justification',
        '  e. Biographical Sketch',
        '  f. F&A Rate Agreement',
        '  g. Fringe Benefit Rate Agreement',
        '  h. RFP-Specific Documents',
        '    i. current & pending support',
        '    ii. facilities, Equipment and other resources',
        '    iii. Collaborators and Other Affiliations',
        '    iv. Synergistic Activities',
        '    v. Other Docs'
    ], 5, tier1DeadlineCell);

    const tier2DeadlineCell = `$C${tier2StartRow + 1}`;
    const tier1TasksWithNotes = {
        'Cayuse Proposal Submission (complete and approved)': '',
        'Statement of Work': '',
        'Budget (final approved by SPO)': '',
        'Budget Justification': 'https://www.mtu.edu/icc/members/templates/documents/budget-justification-template.docx',
        'Cost Share Approval Documentation': '',
        'Data Management Plan': 'https://www.mtu.edu/icc/members/templates/documents/data-management-plan-starter.docx',
        'Facilities, Equipment, and Other Resources': 'https://www.mtu.edu/icc/members/templates/documents/facilities-template.docx',
        'Mentoring Plan': 'https://www.mtu.edu/icc/members/templates/documents/mentoring-plan-starter.docx',
        'Certifications and Representations': '',
        'Cost Proposal Volume': '',
        'Letters of Support': '',
        'Environmental Questionnaire': '',
        'Proposal Shared with AOR (if applicable)': ''
    };
    currentRow = addSectionWithNotes(sheet, currentRow, 'Tier 1 Internal and Non-Science Documents', tier1TasksWithNotes, 4, tier2DeadlineCell);

    currentRow = addSection(sheet, currentRow, 'Tier 2 Science Related and Technical Documents', [
        'Project Summary',
        'Project Description',
        'References Cited',
        'Specific Aims',
        'Research Strategy',
        'Technical/Management Volume'
    ], 1, officialDeadlineCell);

    applyStatusColors(sheet, headerRow + 1, currentRow - 1);

    return currentRow;
}

/**
 * Build PersonnelDocs sheet with Co-PI information
 */
function buildPersonnelDocsSheet(personnelSheet, proposal) {
    let startRow = 1;

    personnelSheet.getRange(startRow, 1).setValue(`PI: ${proposal.pi}`);
    personnelSheet.getRange(startRow, 2).setValue('Co-PI:');
    personnelSheet.getRange(startRow, 3, 1, 2).merge().setValue(`Sponsor: ${proposal.sponsor}`);

    personnelSheet.getRange(startRow + 1, 1).setValue(`Email: ${proposal.email}`);
    personnelSheet.getRange(startRow + 1, 2).setValue('Co-PI:');
    personnelSheet.getRange(startRow + 1, 3).setValue('Official Deadline:');
    if (proposal.deadline) {
        personnelSheet.getRange(startRow + 1, 4).setValue(new Date(proposal.deadline));
        personnelSheet.getRange(startRow + 1, 4).setNumberFormat('MM/dd/yyyy').setHorizontalAlignment('left');
    }

    personnelSheet.getRange(startRow + 2, 2).setValue('Co-PI:');
    personnelSheet.getRange(startRow + 2, 3).setValue('Lead Org Deadline:');
    if (proposal.leadOrgDeadline) {
        personnelSheet.getRange(startRow + 2, 4).setValue(new Date(proposal.leadOrgDeadline));
        personnelSheet.getRange(startRow + 2, 4).setNumberFormat('MM/dd/yyyy').setHorizontalAlignment('left');
    }

    personnelSheet.getRange(startRow + 2, 1).setValue(`Co-Investigators: ${proposal.coInvestigators || ''}`);
    personnelSheet.getRange(startRow + 3, 2).setValue('Co-PI:');
    personnelSheet.getRange(startRow + 3, 3).setValue('Expected Submission:');
    if (proposal.expectedSubmission) {
        personnelSheet.getRange(startRow + 3, 4).setValue(new Date(proposal.expectedSubmission));
        personnelSheet.getRange(startRow + 3, 4).setNumberFormat('MM/dd/yyyy').setHorizontalAlignment('left');
    }

    personnelSheet.getRange(startRow + 4, 2).setValue('Co-PI:');

    personnelSheet.getRange(startRow, 1, 5, 4)
        .setBackground('#ffd966')
        .setFontWeight('bold')
        .setFontSize(12)
        .setBorder(true, true, true, true, false, false);

    const headerRow = startRow + 5;
    personnelSheet.getRange(headerRow, 1, 1, 4).setValues([['Task', 'Status', 'Deadline', 'Notes or Information']]);
    personnelSheet.getRange(headerRow, 1, 1, 4)
        .setBackground('#4a86e8')
        .setFontColor('#ffffff')
        .setFontWeight('bold')
        .setBorder(true, true, true, true, true, true);

    let currentRow = headerRow + 1;
    const officialDeadlineCell = `$D${startRow + 1}`;

    const personnelTasksWithNotes = {
        'Biographical Sketch': '',
        'Current and Pending Support Form': '',
        'Collaborators and Other Affiliations': '',
        'Synergistic Activities': 'https://www.mtu.edu/icc/members/templates/documents/synergistic-activities-starter.docx'
    };

    currentRow = addPersonnelSection(personnelSheet, currentRow, 'PI:', personnelTasksWithNotes, officialDeadlineCell);

    for (let i = 1; i <= 5; i++) {
        currentRow = addPersonnelSection(personnelSheet, currentRow, 'Co-PI:', personnelTasksWithNotes, officialDeadlineCell);
    }

    personnelSheet.setColumnWidth(1, 300);
    personnelSheet.setColumnWidth(2, 150);
    personnelSheet.setColumnWidth(3, 160);
    personnelSheet.setColumnWidth(4, 400);

    applyStatusColors(personnelSheet, headerRow + 1, currentRow - 1);
}

/**
 * Apply conditional formatting for status colors
 */
function applyStatusColors(sheet, startRow, endRow) {
    const statusColumn = 2;
    const range = sheet.getRange(startRow, statusColumn, endRow - startRow + 1, 1);
    const rules = sheet.getConditionalFormatRules();

    const notStartedRule = SpreadsheetApp.newConditionalFormatRule()
        .whenTextEqualTo('Not Started')
        .setBackground('#B10202')
        .setFontColor('#FFFFFF')
        .setRanges([range])
        .build();

    const inProgressRule = SpreadsheetApp.newConditionalFormatRule()
        .whenTextEqualTo('In Progress')
        .setBackground('#F1CC0F')
        .setFontColor('#000000')
        .setRanges([range])
        .build();

    const completedRule = SpreadsheetApp.newConditionalFormatRule()
        .whenTextEqualTo('Completed')
        .setBackground('#11734B')
        .setFontColor('#FFFFFF')
        .setRanges([range])
        .build();

    const notApplicableRule = SpreadsheetApp.newConditionalFormatRule()
        .whenTextEqualTo('Not Applicable')
        .setBackground('#3D3D3D')
        .setFontColor('#FFFFFF')
        .setRanges([range])
        .build();

    rules.push(notStartedRule, inProgressRule, completedRule, notApplicableRule);
    sheet.setConditionalFormatRules(rules);
}
