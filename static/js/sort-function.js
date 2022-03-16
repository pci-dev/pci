$(document).ready(function(){
	// attach onclick sort function for Roles table column (user list)
	var columns = document.querySelectorAll('.web2py_htmltable > table th');
	if (columns) {
		for (var i = 0; i < columns.length; i++) {
			if (columns[i].innerHTML == 'Roles') {
				columns[i].classList.add('cp');
				columns[i].setAttribute('onclick', 'sort_by_role(7)');
			}
		}
	}
})

// function that sorts a HTML table according to the Roles column
function sort_by_role(n) {
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

	// finally remove sort icon on other column heads and attach to Roles column
	var column_heads = document.querySelectorAll('.web2py_htmltable > table th');
	for (var i = 0; i < column_heads.length; i++) {
		var link = column_heads[i].querySelector('a');
		if (link) {
			if (link.innerHTML.includes('▲') || link.innerHTML.includes('▼')) {
				link.innerHTML = link.innerHTML.slice(0, -1);
			}
		}
		if (column_heads[i].innerHTML.includes('Roles')) {
			if (dir == 'asc') { column_heads[i].innerHTML = 'Roles▲'}
			else { column_heads[i].innerHTML = 'Roles▼' }
		}
	}
}
