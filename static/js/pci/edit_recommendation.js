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
  const decisonRecommendationLabelInitialSubText =  getDecisonRecommendationLabelInitialSubText();
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

  function getDecisonRecommendationLabelInitialSubText() {
    if (pciRRactivated) {
      return `
        The recommendation text is a short article, similar to a News & Views piece. It contains between 300 and 1500 words, describes the context, explains why you found interesting the article, and why you decided to recommend it. This text also contains references (at a minimum the reference to the article being recommended). The recommendation should contain the following points:
        <ul style="margin-top: 5px">
          <li>scientific context (with references)</li>
          <li>questions, hypotheses, methodology</li>
          <li>main results and interpretations</li>
          <li>Most importantly, please develop the reasons why you decided to recommend it</li>
        </ul>
        Reviews related to your Recommendation decision will be automatically included in the email to authors after the managing board validates your decision. There's no need to copy/paste them into this box.
        `;
    } else {
      return `
        <div style="line-height: 1.3em">
          <p>The recommendation text is a short article, similar to a News & Views piece. It contains between 300 and 1500 words, describes the context, explains why you found the article interesting, and why you decided to recommend it. This text also contains references (at a minimum, the reference to the recommended article). The recommendation should include the following points:</p>
          <ul style="margin-top: 5px">
            <li>scientific context (with references)</li>
            <li>questions, hypotheses, methodology</li>
            <li>main results and interpretations</li>
            <li>Most importantly, please develop the reasons why you decided to recommend it</li>
          </ul>
          <p>Here are some questions to help you write your recommendation text:</p>
          <h5>1- What is the general context of the study in the field?</h5>
          <pre>[The general context of the study is ...]</pre>
          <h5>2- What is your specific interest in the scientific question asked by / the object studied in the article?</h5>
          <pre>[I'm particularly interested in ...]</pre>
          <h5>3- What is your specific interest in the methodology, the robustness, the results or the discussion of the article?</h5>
          <pre>[I evaluated this article because the methodology/robustness/results/discussion are ...]</pre>
          <h5>4- Besides the above points, is there any other reason you decided to accept the role of recommender for this article? (You should make it clear it was due to one or both of the above points if not)</h5>
          <pre>[I decided to accept the role of recommender for this article because ...]</pre>
          <h5>5- Is there a particular way the authors decided to tackle these questions? What was notable?</h5>
          <pre>[The authors used a new experimental design; new software; …]</pre>
          <h5>6- Very concisely, what are the main results of the study? (Note that this is not meant to reiterate the abstract -- a succinct high-level summary is generally best)</h5>
          <pre>[The authors used X and Y to show that Z is consistent over…]</pre>
          <h5>7- Were any notable study aspects improved due to feedback from the reviewers/recommender? Especially in scientific content, such as new analyses that resolved ambiguity.</h5>
          <pre>[One reviewer noted an issue with the author’s original method, which was improved in a
subsequent version by…]</pre>
          <h5>8- What were the points that the reviewers positively evaluated in their review?</h5>
          <pre>[During the peer-review process, the reviewers particularly appreciated ...]</pre>
          <h5>9- What were the points that you, as a recommender, particularly appreciated in the work?</h5>
          <pre>[I found tool Y finding X particularly interesting, because … ]</pre>
          <br />
          <p>Reviews related to your Recommendation decision will be automatically included in the email to authors after the managing board validates your decision. There's no need to copy/paste them into this box</p>
        <div>
        `;
    }
  }
}
