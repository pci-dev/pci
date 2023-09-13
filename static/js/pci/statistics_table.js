let table = document.querySelector('.statistics table');

if (table) {
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
}