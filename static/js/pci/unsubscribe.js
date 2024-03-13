window.addEventListener('DOMContentLoaded', () => {
	const submitButton = document.querySelector('input[type=submit]');
	submitButton.addEventListener('click', confirmationDialogFunction);
});

function confirmationDialogFunction(e) {
	e.preventDefault();
	const unsubscribeChekbox = document.getElementById('unsubscribe_checkbox');
	const form = document.getElementsByTagName('form')[0]

	if (!unsubscribeChekbox.checked) {
		form.submit();
		return;
	}

	$('#confirmation-modal')
		.modal('show')
		.on('click', '#confirm-dialog', function (e) {
		location.href = e.target.attributes.redirect.value;
		});

	$('#cancel-dialog').on('click', function () {
		return;
	});
}
