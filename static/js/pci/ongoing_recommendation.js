function showInfoDialogBeforeValidateRecommendation(e) {
    e.preventDefault();

    $('#info-dialog').modal('show')
        .on('click', '#confirm-dialog', function () {
            $('#info-dialog').submit()
        });

    $('#cancel-dialog')
        .on('click', function () { return; });
}
