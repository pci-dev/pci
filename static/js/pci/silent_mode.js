const forms = document.querySelectorAll('form');

forms.forEach(form => {
    const silentModeCheckbox = document.createElement('input');
    silentModeCheckbox.type = 'checkbox';
    silentModeCheckbox.name = 'silent_mode';
    silentModeCheckbox.id = 'silent_mode';
    silentModeCheckbox.value = 'true';

    const labelSilentModeCheckbox = document.createElement('label');
    labelSilentModeCheckbox.for = 'silent_mode';
    labelSilentModeCheckbox.append('Silent Mode');

    const divSilentMode = document.createElement('div')
    divSilentMode.appendChild(silentModeCheckbox);
    divSilentMode.appendChild(labelSilentModeCheckbox);

    let submitButton = form.querySelector('input[type=submit]');
    if (submitButton == null) {
        form.insertBefore(divSilentMode, form.lastChild);
    } else {
        const parentSubmit = submitButton.parentNode;
        parentSubmit.insertBefore(divSilentMode, submitButton);

    }
});
