var table = document.querySelector('.statistics table');
var lastSortedColumn = -1;
var sortAscending = true;

if (table) {
    window.onload = function() {
        let first_header = table.querySelector("th");
        first_header.setAttribute('onclick', 'sortTable(0)');
        first_header.classList.add('cp');
        let header_link = first_header.querySelector('a');
        header_link.removeAttribute('href');

    }

    let rows = table.querySelectorAll('tbody tr');
    let highest = 0;
    for (let i=0; i<rows.length; i++) {
        if (rows[i].offsetHeight > highest) {
            highest = rows[i].offsetHeight;
        }
    }
    for (let i=0; i<rows.length; i++) {
        $(rows[i]).height(highest);
    }

    sortTable(0);
}


function sortTable(columnIndex) {
    let rows = Array.from(table.rows).slice(1); // Get all rows except the header
    let sortedRows;

    if (lastSortedColumn === columnIndex) {
        // If the same column was clicked again, reverse the sort direction
        sortAscending = !sortAscending;
    } else {
        // If a new column was clicked, sort in ascending order
        sortAscending = true;
        lastSortedColumn = columnIndex;
    }

    // Sort the rows based on the clicked header (column)
    if (columnIndex === 0) { // If sorting by name
        sortedRows = rows.sort((a, b) => a.cells[columnIndex].innerText.localeCompare(b.cells[columnIndex].innerText));
    } else { // If sorting by other columns like age (assuming they are numbers)
        sortedRows = rows.sort((a, b) => a.cells[columnIndex].innerText - b.cells[columnIndex].innerText);
    }

    // If sorting in descending order, reverse the sorted rows
    if (!sortAscending) {
        sortedRows.reverse();
    }

    // Append sorted rows back to the table
    sortedRows.forEach(row => table.tBodies[0].appendChild(row));
}