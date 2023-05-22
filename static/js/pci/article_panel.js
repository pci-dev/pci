function checkPanel(panelId, iconId){
    if(jQuery(panelId).hasClass('pci2-panel-closed')) { 
      jQuery(panelId).removeClass('pci2-panel-closed') 
      jQuery(iconId).removeClass('glyphicon-rotate') 
      jQuery(iconId).addClass('glyphicon-rotate-reversed') 
    } else {
      jQuery(panelId).addClass('pci2-panel-closed') 
      jQuery(iconId).removeClass('glyphicon-rotate-reversed') 
      jQuery(iconId).addClass('glyphicon-rotate')
    }
  };
