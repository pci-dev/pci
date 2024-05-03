var button = document.getElementById("cancel-submission-button");
if (button) {
	confirmCancellation = function (e) {
		if (!confirm("{{=T('Are you sure you want to proceed?')}}")) {
			e.preventDefault()
		}
	}

	button.onclick = confirmCancellation
}

function colorHypothesisButton() {

	if (!$('#hypothesis_button_container').length) {
		return;
	}

	const url = new URL(window.location.href);
	const searchParams = new URLSearchParams(url.search);
	const articleId = searchParams.get('articleId');

	$.ajax({
		type: 'POST',
		url: 'color_hypothesis_button',
		data: { article_id: articleId },
		success: function(response) {
			$('#hypothesis_button_container').html(response)
		}
	})
}

$(document).ready(colorHypothesisButton);

function callNotConsideredDialog(event, article_id, url) {
	event.preventDefault();
	showSetNotConsideredDialog(article_id, url);
}

function confirmationDialogFunction(e) {
	e.preventDefault();
	$('#confirmation-modal').modal('show')
		.on('click', '#confirm-dialog', function(){
			location.href = goLink;
		});

	$('#cancel-dialog')
		.on('click',function(){ return; });
}
