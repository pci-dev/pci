function showInfoDialogBeforeValidateRecommendation(e) {
    e.preventDefault();

    $('#info-dialog').modal('show')
        
    $('#confirm-dialog').on('click', function (e) {
            $('#info-dialog').submit();
            return false;
        });

    $('#cancel-dialog')
        .on('click', function () { return; });
}
