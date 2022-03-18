$(document).ready(function(){
	// add js-based column sorting
	var page_name = document.querySelector('.pci-text-title p');
	if (page_name) {
		if (page_name.innerHTML == 'Users &amp; roles') {
			var columns = document.querySelectorAll('.web2py_htmltable > table th');
			if (columns) {
				for (var i = 0; i < columns.length; i++) {
					if (!columns[i].innerHTML == '') {
						columns[i].setAttribute('onclick', 'sort_by(' + i + ')');
						columns[i].classList.add('cp');
					}
				}
			}
		}
	}
})


// sort a web2py grid/smartgrid HTML table according to column at index n
function sort_by(n) {
	// gather variables (parameter n is the column index)
	var table, rows, switching, i, x, y, shouldSwitch, dir, switchcount = 0;
	table = document.querySelector('.web2py_htmltable > table');
	switching = true;

	// Sorting direction
	dir = "asc";

	// switch loop
	while (switching) {
	  switching = false;
	  rows = table.rows;
	  for (i = 1; i < (rows.length - 1); i++) {
		shouldSwitch = false;
		x = rows[i].getElementsByTagName("TD")[n];
		y = rows[i + 1].getElementsByTagName("TD")[n];
		if (dir == "asc") {
		  if (x.innerHTML.toLowerCase() > y.innerHTML.toLowerCase()) {
			shouldSwitch = true;
			break;
		  }
		} else if (dir == "desc") {
		  if (x.innerHTML.toLowerCase() < y.innerHTML.toLowerCase()) {
			shouldSwitch = true;
			break;
		  }
		}
	  }

	  // switch rows
	  if (shouldSwitch) {
		rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
		switching = true;
		switchcount ++;
	  } else {
		if (switchcount == 0 && dir == "asc") {
		  dir = "desc";
		  switching = true;
		}
	  }
	}

	// finally remove sort icon on other column heads
	var column_heads = document.querySelectorAll('.web2py_htmltable > table th');
	for (var i = 0; i < column_heads.length; i++) {
		if (column_heads[i].innerHTML.includes('▲') || column_heads[i].innerHTML.includes('▼')) {
			column_heads[i].innerHTML = column_heads[i].innerHTML.slice(0, -1);
		}
	}

	// then attach triangle to active column
	var active_column = column_heads[n];
	if (dir == 'asc') { active_column.innerHTML += '▲'}
	else { active_column.innerHTML += '▼' }
}
