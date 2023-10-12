document.getElementById('auth_user_orcid').addEventListener('input', function() {
    var orcid_value = this.value.split("-").join("");
    if (orcid_value.length > 0) {
        orcid_value = orcid_value.match(new RegExp('.{1,4}', 'g')).join("-");
    }
    this.value = orcid_value;
})
