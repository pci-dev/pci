/**

   Created and copyrighted by Massimo Di Pierro <massimo.dipierro@gmail.com>
   (MIT license)  

   Example:

   <script src="share.js"></script>

**/

(function(d, s, id) {
	var js, fjs = d.getElementsByTagName(s)[0];
	if (d.getElementById(id)) return;
	js = d.createElement(s); js.id = id;
	js.src = "//connect.facebook.net/en_US/sdk.js#xfbml=1&version=v2.8";
	fjs.parentNode.insertBefore(js, fjs);
}(document, 'script', 'facebook-jssdk'));


jQuery(function(){
	var script_source = jQuery('script[src*="share.js"]').attr('src');
        var params = function(name,default_value) {
            var match = RegExp('[?&]' + name + '=([^&]*)').exec(script_source);
            return match && decodeURIComponent(match[1].replace(/\+/g, ' '))||default_value;
        }
    var hh='32px';
	var hho=52;
	var ww='70px';
	var wwo=64;
	var path = params('static','social');
	var url = encodeURIComponent(window.location.href);
	var host =  window.location.hostname;
	var title = escape(jQuery('title').text());
	
	var twit = '<a class="twitter-share-button" style="margin-top:8px;" href="https://twitter.com/intent/tweet?url='+url+'" data-size="large">Tweet</a>';
	
	var facebook = '<div class="fb-share-button" data-href="'+url+'" data-layout="button" data-size="large"></div>';
	
	var gplus = '<a href="https://plus.google.com/share?url='+url+'" style="vertical-align:top;" onclick="javascript:window.open(this.href, \'\', \'menubar=no,toolbar=no,resizable=yes,scrollbars=yes\');return false;"><img src="https://www.gstatic.com/images/icons/gplus-32.png" alt="Share on Google+"/></a>';
	
	var tbar = '<div id="socialdrawer"><span>Share<br/></span><div id="sicons">'
	if (typeof twit !== 'undefined') {
		tbar += twit
		wwo += 80
	}
	if (typeof facebook !== 'undefined') {
		tbar += facebook
		wwo += 80
	}
	if (typeof gplus !== 'undefined') {
		tbar += gplus
		wwo += 60
	}
	tbar += '</div></div>';
	wwo=wwo.toString()+'px';
	hho=hho.toString()+'px';
	
	// Add the share tool bar.
	jQuery('body').append(tbar); 
	var st = jQuery('#socialdrawer');
	var si = jQuery('#sicons');
	st.css({'opacity':'1.0', 'background':'#0db9f2', 
				'z-index':'3000',
				'border':'solid 1px #666666','border-width':' 1px 1px 1px 1px',
				'height':hho,
				'width':wwo,
				'position':'fixed','bottom':'2px','right':'8px',
				'padding':'2px 5px',
				'overflow':'hidden',
				'-webkit-border-top-left-radius':' 12px','-moz-border-radius-topleft':' 12px','border-top-left-radius':' 12px',
				'-webkit-border-top-right-radius':' 12px','-moz-border-radius-topright':' 12px','border-top-right-radius':' 12px',
				'-moz-box-shadow':' -2px -2px 2px 2px rgba(0,0,0,0.5)','-webkit-box-shadow':' -2px -2px 2px 2px rgba(0,0,0,0.5)','box-shadow':' -2px -2px 2px 2px rgba(0,0,0,0.5)'
	});
	jQuery('#sicons').css({'padding-top':'2px'});
	jQuery('#sicons a').css({'padding-left':'4px', 'padding-right':'4px', 'height':'32px', 'vertical-align':'top', 'margin-bottom':'auto'});
	jQuery('#sicons div').css({'padding-left':'4px', 'padding-right':'4px', 'height':'32px', 'vertical-align':'top', 'margin-bottom':'auto'});
	jQuery('#socialdrawer span').css({'float':'left', 'margin':'2px 8px', 'text-shadow':'1px 1px 1px #101010', 'color':'#ffffff', 'font-size':'16px', 'line-height':'1em'});
	
	// hover or click
	//st.mouseover(function(){
	st.click(function(){
		st.animate({height:hho, width:wwo, opacity:1.0});
		si.animate({opacity:1});
	});
	
	//leave
	st.mouseleave(function(){ 
		si.animate({opacity:0});
	    st.animate({height:hh, width:ww, opacity:0.66}); 
	    return false;
	});
	
	// timeout after loading
	setTimeout(function(){
		si.animate({opacity:0}, 1000);
		st.animate({height:hh, width:ww, opacity:0.66}, 2000); 
	}, 5000);
});
