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

    let params = new URLSearchParams(window.location.search);
    if (!params.has('order')) {
        sortTable(0);
    }
}


function sortTable(columnIndex) {
    let rows = Array.from(table.rows).slice(1);
    let sortedRows;

    if (lastSortedColumn === columnIndex) {
        sortAscending = !sortAscending;
    } else {
        sortAscending = true;
        lastSortedColumn = columnIndex;
    }

    if (columnIndex === 0) { 
        sortedRows = rows.sort((a, b) => a.cells[columnIndex].innerText.localeCompare(b.cells[columnIndex].innerText));
    } else { 
        sortedRows = rows.sort((a, b) => a.cells[columnIndex].innerText - b.cells[columnIndex].innerText);
    }

    if (!sortAscending) {
        sortedRows.reverse();
    }

    sortedRows.forEach(row => table.tBodies[0].appendChild(row));
    reapply_row_colours();
}


function reapply_row_colours() {
    let rows = Array.from(table.rows).slice(1);
    rows.forEach((row, index) => {
        if (index % 2 !== 0) {
          row.classList.add('w2p_even');
          row.classList.add('even');
          if (row.classList.contains('w2p_odd')) {
            row.classList.remove('w2p_odd');
            row.classList.remove('odd');
          }
        }
        else {
            row.classList.add('w2p_odd');
            row.classList.add('odd');            
            if (row.classList.contains('w2p_even')) {
                row.classList.remove('w2p_even');
                row.classList.remove('even');
            }
        }
    });
}