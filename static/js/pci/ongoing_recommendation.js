function showInfoDialogBeforeValidateRecommendation(e) {
    e.preventDefault();

    $('#info-dialog').modal('show')
        .on('click', '#confirm-dialog', function () {
            document.location.href = document.getElementById('do_recommend_article').getAttribute('href');
        });

    $('#cancel-dialog')
        .on('click', function () { return; });
}