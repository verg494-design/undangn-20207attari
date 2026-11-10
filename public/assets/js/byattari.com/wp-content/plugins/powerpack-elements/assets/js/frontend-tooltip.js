(function ($) {
    'use strict';

    var isEditMode = false;

    var getElementSettings = function( $element ) {
		var elementSettings = {},
			modelCID 		= $element.data( 'model-cid' );

		if ( isEditMode && modelCID ) {
			var settings     = elementorFrontend.config.elements.data[ modelCID ],
				settingsKeys = elementorFrontend.config.elements.keys[ settings.attributes.widgetType || settings.attributes.elType ];

			jQuery.each( settings.getActiveControls(), function( controlKey ) {
				if ( -1 !== settingsKeys.indexOf( controlKey ) ) {
					elementSettings[ controlKey ] = settings.attributes[ controlKey ];
				}
			} );
		} else {
			elementSettings = $element.data('settings') || {};
		}

		return elementSettings;
	};

	var ElementsTooltipHandler = function( $scope, $ ) {
		var elementSettings = getElementSettings( $scope ),
			isTooltip       = elementSettings.pp_elements_tooltip_enable;

		if ( 'yes' !== isTooltip ) {
			return;
		}

		var tooltipElem     = $scope,
			id              = $scope.data('id'),
			ppclass         = 'pp-tooltip' + ' pp-tooltip-' + id,
			ttPosition      = elementSettings.pp_elements_tooltip_position,
			ttArrow         = elementSettings.pp_elements_tooltip_arrow,
			ttTarget        = elementSettings.pp_elements_tooltip_target,
			ttSelector      = elementSettings.pp_elements_tooltip_selector,
			ttTrigger       = elementSettings.pp_elements_tooltip_trigger,
			ttDistance      = ( '' !== elementSettings.pp_elements_tooltip_distance && undefined !== elementSettings.pp_elements_tooltip_distance ) ? elementSettings.pp_elements_tooltip_distance.size : '',
			animation       = elementSettings.pp_elements_tooltip_animation,
			tooltipWidth    = ( '' !== elementSettings.pp_elements_tooltip_width && undefined !== elementSettings.pp_elements_tooltip_width ) ? elementSettings.pp_elements_tooltip_width.size : '',
			tooltipZindex   = elementSettings.pp_elements_tooltip_zindex;

		if ( 'custom' === ttTarget ) {
			if ( '' !== ttSelector ) {
				var target = $scope.find( ttSelector );

				if ( ttSelector.length ) {
					tooltipElem = target;
				}
			}
		}

		if ( $scope.hasClass('tooltipstered') ) {
			$scope.pptooltipster('destroy');
		}

		if ( tooltipElem.hasClass('tooltipstered') ) {
			$(tooltipElem).pptooltipster('destroy');
		}

		$(tooltipElem).pptooltipster({
			trigger:         ttTrigger,
			content:         $scope.find('#pp-tooltip-content-' + id),
			animation:       animation,
			minWidth:        0,
			maxWidth:        tooltipWidth,
			ppclass:         ppclass,
			position:        ttPosition,
			arrow:           ( 'yes' === ttArrow ),
			distance:        ttDistance,
			interactive:     true,
			positionTracker: true,
			zIndex:          tooltipZindex,
			functionInit:   function(instance, helper) {
				var content = $scope.find('#pp-tooltip-content-' + id).detach();
				instance.content(content);
			}
		});
	};
    
    $(window).on('elementor/frontend/init', function () {
        if ( elementorFrontend.isEditMode() ) {
			isEditMode = true;
		}

		elementorFrontend.hooks.addAction( 'frontend/element_ready/widget', ElementsTooltipHandler );
    });
    
}(jQuery));
