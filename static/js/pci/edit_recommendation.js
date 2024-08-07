jQuery(document).ready(function() {
  jQuery("#t_recommendations_no_conflict_of_interest").click(function() {
    jQuery(":submit[name=terminate]").prop(
      "disabled",
      !(
        jQuery("#t_recommendations_no_conflict_of_interest").prop("checked") &
        ($("#opinion_recommend").prop("checked") |
          $("#opinion_revise").prop("checked") |
          $("#opinion_reject").prop("checked") |
          $("#opinion_recommend_private").prop("checked")
        )
      )
    );
  });
  jQuery("input[type=radio][name=recommender_opinion]").change(function() {
    jQuery(":submit[name=terminate]").prop(
      "disabled",
      !(
        jQuery("#t_recommendations_no_conflict_of_interest").prop("checked") &
        ($("#opinion_recommend").prop("checked") |
          $("#opinion_revise").prop("checked") |
          $("#opinion_reject").prop("checked") |
          $("#opinion_recommend_private").prop("checked")
        )
      )
    );
  });
  jQuery(":submit[name=terminate]").prop(
    "disabled",
    !(
      jQuery("#t_recommendations_no_conflict_of_interest").prop("checked") &
      ($("#opinion_recommend").prop("checked") |
        $("#opinion_revise").prop("checked") |
        $("#opinion_reject").prop("checked") |
        $("#opinion_recommend_private").prop("checked")
      )
    )
  );
});

///////////////////////////////

let updateRecommendContent = true;

if (!pciRRactivated) {
  function updateDisplayForm(el, initial) {
    showForm();

    if (['opinion_revise', 'opinion_reject'].includes(el.id)) {
      if (updateRecommendContent) {
        fileInputLabel.textContent = fileInputLabelInitial;
        recommendationTitleInputInitalValue = recommendationTitleInput.value;
        if (!initial && tinymce.get('t_recommendations_recommendation_comments')) {
          const currentContent = tinymce.get('t_recommendations_recommendation_comments')?.getContent();
          if (currentContent) {
            decisonRecommendationCommentRecommended = currentContent;
          }
          tinymce.get('t_recommendations_recommendation_comments')?.setContent(decisonRecommendationCommentOther);
        }
        updateRecommendContent = false;
      }

      recommendationTitleRow.style.display = 'none';
      recommendationTitleInput.value = '';
      decisonRecommendationLabel.firstChild.nodeValue = 'Decision text';
      decisonRecommendationLabel.lastChild.innerHTML = "Reviews related to your decision will be automatically included in the email to authors after the managing board validates your decision. There's no need to copy/paste them into this box."

    } else {
      fileInputLabel.textContent = 'If you have trouble copying and pasting your recommendation text, please upload it as a PDF, DOCX, or ODT file';
      recommendationTitleRow.style.display = 'flex';
      recommendationTitleInput.value = recommendationTitleInputInitalValue;
      decisonRecommendationLabel.firstChild.nodeValue = decisonRecommendationLabelInitialText;
      decisonRecommendationLabel.lastChild.innerHTML = decisonRecommendationLabelInitialSubText;
      if (!initial && tinymce.get('t_recommendations_recommendation_comments')) {
        decisonRecommendationCommentOther = tinymce.get('t_recommendations_recommendation_comments')?.getContent();
        tinymce.get('t_recommendations_recommendation_comments')?.setContent(decisonRecommendationCommentRecommended);
      }
      updateRecommendContent = true;
    }
  }
  
  const fileInputLabel = document.getElementById('t_recommendations_recommender_file__label');
  const fileInputLabelInitial = fileInputLabel.textContent;

  const opinionRecommendCheckbox = document.getElementById('opinion_recommend');
  const opinionReviseCheckbox = document.getElementById('opinion_revise');
  const opinionRejectCheckbox = document.getElementById('opinion_reject');

  hideForm();
  
  opinionRecommendCheckbox.addEventListener('change', (e) => {updateDisplayForm(e.target, false)});
  opinionReviseCheckbox.addEventListener('change', (e) => {updateDisplayForm(e.target, false)});
  opinionRejectCheckbox.addEventListener('change', (e) => {updateDisplayForm(e.target, false)});
  
  const recommendationTitleRow = document.getElementById('t_recommendations_recommendation_title__row');
  
  const recommendationTitleInput = document.getElementById('t_recommendations_recommendation_title');
  let recommendationTitleInputInitalValue = recommendationTitleInput.value;
  
  const decisonRecommendationLabel = document.querySelector('#t_recommendations_recommendation_comments__label > span');
  const decisonRecommendationLabelInitialText = decisonRecommendationLabel.firstChild.nodeValue;
  const decisonRecommendationLabelInitialSubText = `
  The recommendation text is a short article, similar to a News & Views piece. It contains between 300 and 1500 words, describes the context, explains why you found interesting the article, and why you decided to recommend it. This text also contains references (at a minimum the reference to the article being recommended). The recommendation should contain the following points:
  <ul style="margin-top: 5px">
    <li>scientific context (with references)</li>
    <li>questions, hypotheses, methodology</li>
    <li>main results and interpretations</li>
    <li>Most importantly, please develop the reasons why you decided to recommend it</li>
  </ul>
  Reviews related to your Recommendation decision will be automatically included in the email to authors after the managing board validates your decision. There's no need to copy/paste them into this box.
  `;

  let decisonRecommendationCommentOther = "";
  
  let once = false;
  var observerForTinyMce = new MutationObserver(() => {
      if (once || !tinymce.get('t_recommendations_recommendation_comments')) {
        return;
      }
      once = true;

      if (opinionRecommendCheckbox.checked) {
        const value = tinymce.get('t_recommendations_recommendation_comments')?.getContent();
        if (value) {
          decisonRecommendationCommentRecommended = value;
        } else {
          tinymce.get('t_recommendations_recommendation_comments').setContent(decisonRecommendationCommentRecommended);
        }
      } else {
        decisonRecommendationCommentOther = tinymce.get('t_recommendations_recommendation_comments')?.getContent();
      }
      
      document.querySelectorAll('.tox-edit-area__iframe').forEach((tinymceForm) => {
        if (opinionRecommendCheckbox.checked) {
          updateDisplayForm(opinionRecommendCheckbox, true);
        }
      
        if (opinionReviseCheckbox.checked) {
          updateDisplayForm(opinionReviseCheckbox, true);
        }
      
        if (opinionRejectCheckbox.checked) {
          updateDisplayForm(opinionRejectCheckbox, true);
        }
      });    
  });
  observerForTinyMce.observe(document.body, { childList: true, subtree: true });


  function hideForm() {
    if (!opinionRecommendCheckbox.checked && !opinionRejectCheckbox.checked && !opinionReviseCheckbox.checked) {
      document.querySelectorAll('form > div').forEach((divEl) => {
        if (divEl.querySelector('#opinion_recommend') == null) {
          divEl.style.display = 'none';    
        }
      });
    }
  }
  
  function showForm() {
    if (opinionRecommendCheckbox.checked || opinionRejectCheckbox.checked || opinionReviseCheckbox.checked) {
      document.querySelectorAll('form > div').forEach((divEl) => {
        if (divEl.querySelector('#opinion_recommend') == null) {
          divEl.style.display = 'flex';    
        }
      });
    }
  }
}
