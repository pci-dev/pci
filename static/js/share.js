/**
   Created and copyrighted by Massimo Di Pierro <massimo.dipierro@gmail.com>
   (MIT license)  
   Example: <script src="share.js"></script>
**/


jQuery(function(){
	var script_source = jQuery('script[src*="share.js"]').attr('src');
        var params = function(name,default_value) {
            var match = RegExp('[?&]' + name + '=([^&]*)').exec(script_source);
            return match && decodeURIComponent(match[1].replace(/\+/g, ' '))||default_value;
        }
    var hh='36px';
	var ww='90px';
	var wwo = '550px';
	var hho = '500px';
	var path = params('static','social');
	var url = encodeURIComponent(window.location.href);
	var host =  window.location.hostname;
	var title = escape(jQuery('title').text());
	
	tbar = '<div id="socialdrawer"><div id="socialTitle"><span id="socialFold" style="cursor:se-resize;">Share&nbsp;↘</span><span id="socialUnfold" style="cursor:nw-resize;">Share&nbsp;↖</span></div><div id="sicons"><div data-social-share-privacy="true"></div></div></div>'
	
	// Add the share tool bar.
	jQuery('body').append(tbar); 
	var st = jQuery('#socialdrawer');
	var stt = jQuery('#socialTitle');
	var sf = jQuery('#socialFold');
	var su = jQuery('#socialUnfold');
	var si = jQuery('#sicons');
	st.css({'opacity':'0.67', 'background':'#0db9f2', 
				'z-index':'3000',
				'border':'solid 1px #666666','border-width':' 1px 1px 1px 1px',
				'height':hh,
				'width':ww,
				'position':'fixed','bottom':'2px','right':'8px',
				'padding':'2px 5px',
				'overflow':'hidden',
				'-webkit-border-top-left-radius':' 12px','-moz-border-radius-topleft':' 12px','border-top-left-radius':' 12px',
				'-webkit-border-top-right-radius':' 12px','-moz-border-radius-topright':' 12px','border-top-right-radius':' 12px',
				'-moz-box-shadow':' -2px -2px 2px 2px rgba(0,0,0,0.5)','-webkit-box-shadow':' -2px -2px 2px 2px rgba(0,0,0,0.5)','box-shadow':' -2px -2px 2px 2px rgba(0,0,0,0.5)'
	});
	si.css({
				'overflow-y':'auto', 
				'overflow-x':'hidden', 
				'height':'100%', 
				'opacity':'0'
	});
	stt.css({'float':'left', 'margin':'2px 8px', 'text-shadow':'1px 1px 1px #101010', 'color':'#ffffff', 'font-size':'16px', 'line-height':'1em', 'opacity':'1'});
	sf.hide();
	
	// click
	su.click(function(){
		st.animate({height:hho, width:wwo, opacity:1.0});
		si.animate({opacity:1});
		su.hide();
		sf.show();
	});
	
	//leave
	sf.click(function(){ 
		si.animate({opacity:0});
	    st.animate({height:hh, width:ww, opacity:0.67}); 
		sf.hide();
		su.show();
	    return false;
	});
});
