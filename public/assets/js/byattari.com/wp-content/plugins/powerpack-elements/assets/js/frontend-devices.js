(function ($) {
	$( window ).on( 'elementor/frontend/init', () => {
		class DevicesWidget extends elementorModules.frontend.handlers.Base {
			getDefaultSettings() {
				return {
					selectors: {
						outerWrap: '.pp-video',
						videoPlay: '.pp-video-play',
						videoOverlay: '.pp-video-overlay',
						playButton: '.pp-player-controls-play',
						screen: '.pp-device-screen',
						volumeBar: '.pp-player-controls-volume-bar',
						deviceContainer: '.pp-device-container',
						swiperContainer: '.pp-swiper-slider',
						swiperSlide: '.swiper-slide',
					},
				};
			}

			getDefaultElements() {
				const selectors = this.getSettings( 'selectors' );
				return {
					$outerWrap: this.$element.find( selectors.outerWrap ),
					$videoPlay: this.$element.find( selectors.videoPlay ),
					$videoOverlay: this.$element.find( selectors.videoOverlay ),
					$playButton: this.$element.find( selectors.playButton ),
					$screen: this.$element.find( selectors.screen ),
					$volumeBar: this.$element.find( selectors.volumeBar ),
					$deviceContainer: this.$element.find( selectors.deviceContainer ),
					$swiperContainer: this.$element.find( selectors.swiperContainer ),
					$swiperSlide: this.$element.find( selectors.swiperSlide ),
				};
			}

			getSliderSettings(prop) {
				const sliderSettings = ( undefined !== this.elements.$swiperContainer.data('slider-settings') ) ? this.elements.$swiperContainer.data('slider-settings') : '';

				if ( 'undefined' !== typeof prop && 'undefined' !== sliderSettings[prop] ) {
					return sliderSettings[prop];
				}

				return sliderSettings;
			}

			getEffect() {
				return this.getSliderSettings('effect');
			}

			getSwiperOptions() {
				const sliderSettings = this.getSliderSettings();

				const swiperOptions = {
					grabCursor:              'yes' === sliderSettings.grab_cursor,
					// initialSlide:             this.getInitialSlide(),
					slidesPerView:            1,
					slidesPerGroup:           1,
					loop:                     'yes' === sliderSettings.loop,
					centeredSlides:           'yes' === sliderSettings.centered_slides,
					speed:                    sliderSettings.speed,
					autoHeight:               sliderSettings.auto_height,
					effect:                   this.getEffect(),
					preventClicksPropagation: false,
					slideToClickedSlide:      true,
				};

				if ( 'fade' === this.getEffect() ) {
					swiperOptions.fadeEffect = {
						crossFade: true,
					};
				}

				if ( 'yes' === sliderSettings.keyboard ) {
					swiperOptions.keyboard = {
						enabled: true,
					};
				}

				if ( sliderSettings.show_arrows ) {
					var prevEle = ( this.isEdit ) ? '.elementor-swiper-button-prev' : '.swiper-button-prev-' + this.getID();
					var nextEle = ( this.isEdit ) ? '.elementor-swiper-button-next' : '.swiper-button-next-' + this.getID();

					swiperOptions.navigation = {
						prevEl: prevEle,
						nextEl: nextEle,
					};
				}

				if ( sliderSettings.pagination ) {
					var paginationEle = ( this.isEdit ) ? '.swiper-pagination' : '.swiper-pagination-' + this.getID();

					swiperOptions.pagination = {
						el: paginationEle,
						type: sliderSettings.pagination,
						clickable: true
					};
				}

				if ( !this.isEdit && sliderSettings.autoplay ) {
					swiperOptions.autoplay = {
						delay: sliderSettings.autoplay_speed,
						disableOnInteraction: !!sliderSettings.pause_on_interaction
					};
				}

				return swiperOptions;
			}

			bindEvents() {
				this.initVideo();
				this.initHostedVideo();

				const deviceSlider = this.$element.find('.pp-device-slider');

				if ( 0 !== deviceSlider.length ) {
					this.initSlider();
				}
			}

			initVideo() {
				let self = this;

				this.elements.$videoPlay.off( 'click' ).on( 'click', function( e ) {
					e.preventDefault();

					const videoPlayer = $(this).find( '.pp-video-player' );

					self.videoPlay( videoPlayer, self.elements.$outerWrap );
				});

				if ( ! elementorFrontend.isEditMode() ) {
					if ( this.elements.$videoPlay.data( 'autoplay' ) == '1' ) {
						self.videoPlay( this.$element.find( '.pp-video-player' ), this.elements.$outerWrap );
					}
				}

				this.orientationControl();
			}

			videoPlay(selector, outerWrap) {
				var $iframe  = $( '<iframe/>' ),
					$vidSrc = selector.data( 'src' );

				if ( 0 === selector.find( 'iframe' ).length ) {
					if ( outerWrap.hasClass( 'pp-video-type-youtube' ) || outerWrap.hasClass( 'pp-video-type-vimeo' ) || outerWrap.hasClass( 'pp-video-type-dailymotion' ) ) {
						$iframe.attr( 'src', $vidSrc );
					}

					$iframe.attr( 'frameborder', '0' );
					$iframe.attr( 'allowfullscreen', '1' );
					$iframe.attr( 'allow', 'autoplay;encrypted-media;' );
					selector.html( $iframe );

					if ( outerWrap.hasClass( 'pp-video-type-hosted' ) ) {
						var hostedVideoHtml = JSON.parse( outerWrap.data( 'hosted-html' ) );

						$iframe.on( 'load', function() {
							var hostedVideoIframe = $iframe.contents().find( 'body' );
							hostedVideoIframe.html( hostedVideoHtml );
							$iframe.contents().find( 'video' ).css( {"width":"100%", "height":"100%"} );
							$iframe.contents().find( 'video' ).attr( 'autoplay','autoplay' );
					   });
				   }
			   }
		  	}

			initHostedVideo() {
				const elementSettings = this.getElementSettings(),
					videoObj          = this.$element.find( '.pp-video-player-source' ),
					video             = videoObj.get(0),
					videoSource       = elementSettings.video_source,
					stopOthers        = elementSettings.stop_others;

				if ( 'yes' === stopOthers ) {
					$("video").on("play", function() {
						$("video").not(this).each(function(index, video) {
							var plybtn = $(video).parent().find('.pp-player-controls-play');
							plybtn.removeClass('pp-pause');
							plybtn.addClass('pp-play');
							video.pause();
						});
					});
				}

				// Player Controls
				this.playerControls(videoObj, video);

				if ( 'hosted' == videoSource ) {
					this.initHostedPlay(video);

					// Screen Play
					this.initScreenPlay(video);
				}
			}

			playerControls(videoObj, video) {
				const elementSettings = this.getElementSettings(),
					playbtn           = this.elements.$playButton,
					rewindbtn         = this.$element.find( '.pp-player-controls-rewind'),
					autoPlay          = elementSettings.autoplay,
					playback_speed    = elementSettings.playback_speed;

				// Get HTML5 video time duration
				videoObj.on('loadedmetadata', function() {
					if ( 'yes' === autoPlay ) {
						playbtn.first().trigger('click');
					}

					// Playback speed.
					video.playbackRate = playback_speed.size;
					var date = new Date(null);
					date.setSeconds(video.duration); // Specify value for SECONDS here
					var timeString = date.toISOString().substr(11, 8);
					this.$element.find( '.pp-player-controls-duration' ).text(timeString);
				}.bind(this));

				// Update HTML5 video current play time
				videoObj.on('timeupdate', function() {
					var currentPos = video.currentTime; //Get currenttime
					var maxduration = video.duration; //Get video duration
					var percentage = 100 * currentPos / maxduration; //in %
					this.$element.find( '.pp-player-control-progress-track.pp-player-control-progress-inner' ).css('width', percentage+'%');
					var date = new Date(null);
					date.setSeconds(video.currentTime); // specify value for SECONDS here
					var timeString = date.toISOString().substr(11, 8);
					this.$element.find( '.pp-player-controls-time' ).text(timeString);

					if ( video.currentTime === video.duration ) {
						this.elements.$screen.removeClass('pp-paused');
						this.elements.$screen.removeClass('pp-playing');
						playbtn.removeClass('pp-pause');
						playbtn.addClass('pp-play');

						if ( playbtn.hasClass( 'pp-play' ) ) {
							playbtn.find( '.fa-play, .e-fas-fa-play' ).show();
							playbtn.find( '.fa-pause, .e-fas-fa-pause' ).hide();
						} else {
							playbtn.find( '.fa-pause, .e-fas-fa-pause' ).show();
							playbtn.find( '.fa-play, .e-fas-fa-play' ).hide();
						}

						this.$element.find( '.pp-player-controls-time' ).text('00:00');
						this.$element.find( '.pp-player-control-progress-track.pp-player-control-progress-inner' ).css('width', '0%');
						this.elements.$videoOverlay.css('opacity', '');
						// is_playing = false;
					}
				}.bind(this));

				// On video play
				videoObj.on('play', function() {
					this.elements.$videoOverlay.css('opacity', '0');
				}.bind(this));

				// On video pause
				videoObj.on('pause', function() {
					this.$element.find( '.pp-player-controls-rewind.pp-video-button' ).show();
					this.elements.$videoOverlay.css('opacity', '');
				}.bind(this));

				// Mute
				this.$element.find( '.pp-player-controls-volume-icon' ).click( function() {
					if( $(this).hasClass('fa-volume-up') ){
						$(this).removeClass('fa-volume-up');
						$(this).addClass('fa-volume-mute');
					}
					else if( $(this).hasClass('fa-volume-mute') ){
						$(this).removeClass('fa-volume-mute');
						$(this).addClass('fa-volume-up');
					}
					video.muted = !video.muted;
					return false;
				});

				// Volume bar
				var volumeDrag = false;   /* Drag status */
				this.elements.$volumeBar.mousedown( function(e) {
					volumeDrag = true;
					this.updateVolumeBar(e.pageX, video);
				}.bind(this));

				this.elements.$volumeBar.mouseup( function(e) {
					if(volumeDrag) {
						volumeDrag = false;
						this.updateVolumeBar(e.pageX, video);
					}
				}.bind(this));

				this.elements.$volumeBar.mousemove( function(e) {
					if(volumeDrag) {
						this.updateVolumeBar(e.pageX, video);
					}
				}.bind(this));

				// Rewind control
				rewindbtn.on('click', function() {
					video.currentTime = 0;
					return false;
				});

				var timeDrag = false;   /* Drag status */
				this.$element.find( '.pp-player-controls-progress' ).mousedown( function(e) {
					timeDrag = true;
					this.updatebar(e.pageX, video);
				}.bind(this));

				this.$element.find( '.pp-player-controls-progress' ).mouseup( function(e) {
					if(timeDrag) {
						timeDrag = false;
						this.updatebar(e.pageX, video);
					}
				}.bind(this));

				this.$element.find( '.pp-player-controls-progress' ).mousemove( function(e) {
					if(timeDrag) {
						this.updatebar(e.pageX, video);
					}
				}.bind(this));

				// Full screen control
				this.initFullScreen(video);
			}

			initHostedPlay(video) {
				const elementSettings = this.getElementSettings(),
					$screen           = this.elements.$screen,
					playbtn           = this.elements.$playButton;
				let restartOnPause = elementSettings.restart_on_pause;

				if ( 'yes' === restartOnPause ) {
					restartOnPause = true;
				}

				playbtn.on("click", function (e) {
					if ( $(this).hasClass('pp-play') ) {
						video.play();
						playbtn.removeClass('pp-play');
						playbtn.addClass('pp-pause');
						$screen.removeClass('pp-paused');
						$screen.addClass('pp-playing');
					}
					else if ( $(this).hasClass('pp-pause') ) {
						video.pause();
						playbtn.removeClass('pp-pause');
						playbtn.addClass('pp-play');
						$screen.removeClass('pp-playing');
						$screen.addClass('pp-paused');
						if ( restartOnPause ) {
							video.currentTime = 0;
						}
					}

					if ( playbtn.hasClass( 'pp-play' ) ) {
						playbtn.find( '.fa-play, .e-fas-fa-play' ).show();
						playbtn.find( '.fa-pause, .e-fas-fa-pause' ).hide();
					} else {
						playbtn.find( '.fa-pause, .e-fas-fa-pause' ).show();
						playbtn.find( '.fa-play, .e-fas-fa-play' ).hide();
					}

					return false;
				});
			}

			initScreenPlay(video) {
				const elementSettings = this.getElementSettings(),
					$screen           = this.elements.$screen,
					playbtn           = this.elements.$playButton,
					show_buttons      = elementSettings.video_show_buttons;
				let is_playing = false;
				
				if ( 'show' === show_buttons ) {
					return;
				}

				$screen.on('click', function (e) {
					if ( $(this).hasClass('pp-device-screen-video') ) {
						if ( !is_playing ) {
							video.play();
							$screen.removeClass('pp-paused');
							$screen.addClass('pp-playing');
							playbtn.removeClass('pp-play');
							playbtn.addClass('pp-pause');
							is_playing = true;
							return;
						}

						if ( is_playing ) {
							video.pause();
							$screen.removeClass('pp-playing');
							$screen.addClass('pp-paused');
							playbtn.removeClass('pp-pause');
							playbtn.addClass('pp-play');
							is_playing = false;
							return;
						}

						if ( playbtn.hasClass( 'pp-play' ) ) {
							playbtn.find( '.fa-play, .e-fas-fa-play' ).show();
							playbtn.find( '.fa-pause, .e-fas-fa-pause' ).hide();
						} else {
							playbtn.find( '.fa-pause, .e-fas-fa-pause' ).show();
							playbtn.find( '.fa-play, .e-fas-fa-play' ).hide();
						}
					}
				});
			}

			initFullScreen(video) {
				const fsControl = this.$element.find( '.pp-player-controls-fs');

				fsControl.on('click', function() {
					if ( video.requestFullscreen ) {
						video.requestFullscreen();
					} else if ( video.webkitRequestFullscreen ) {
						video.webkitRequestFullscreen();
					} else if ( video.webkitEnterFullscreen ) {
						video.webkitEnterFullscreen();
					} else if ( video.mozRequestFullScreen ) {
						video.mozRequestFullScreen();
					} else if ( video.msRequestFullscreen ) {
						video.msRequestFullscreen();
					} else {
						alert('Your browser doesn\'t support fullscreen');
					}
				});
			}

			updateVolumeBar(x, video) {
				var volumebar = this.elements.$volumeBar;

				var position = x - volumebar.offset().left; // Click pos
				var volume = position / volumebar.width();
				var percentage = 100 * volume; // In %

				// Check within range
				if (volume > 1) {
					volume = 1;
					percentage = 100;
				}

				if (volume < 0) {
					volume = 0;
					percentage = 0;
				}

				// Update volume
				video.volume = volume;
				this.$element.find( '.pp-player-controls-volume-bar-amount.pp-player-control-progress-inner' ).css('width', percentage+'%');
			}

			updatebar(x, video) {
				const elementSettings = this.getElementSettings();
				const end_at_last_frame = elementSettings.end_at_last_frame;
				const progress = this.$element.find( '.pp-player-controls-progress' );
				const maxduration = video.duration; // Video duraiton
				const position = x - progress.offset().left; // Click pos
				let percentage = 100 * position / progress.width();

				// Check within range
				if ( percentage > 100 ) {
					percentage = 100;
				}

				if ( percentage < 0 ) {
					percentage = 0;
				}

				// Update progress bar and video currenttime
				video.currentTime = maxduration * percentage / 100;
				this.$element.find( '.pp-player-controls-progress-time.pp-player-control-progress-inner' ).css('width', percentage+'%');

				if ( 'yes' === end_at_last_frame && 'yes' !== loop ) {
					if ( 100 === percentage ){
						this.elements.$playButton.removeClass('pp-pause');
						this.elements.$playButton.addClass('pp-play');
					}
				}
			}

			orientationControl() {
				const self = this;
				let orientationControl = this.$element.find( '.pp-device-orientation .fas.fa-mobile' );

				orientationControl.click( function(e) {
					if ( $(this).hasClass( 'pp-mobile-icon-portrait' ) ){
						self.elements.$deviceContainer.removeClass( 'pp-device-orientation-portrait' );
						self.elements.$deviceContainer.addClass( 'pp-device-orientation-landscape' );
						$(this).removeClass( 'pp-mobile-icon-portrait' );
						$(this).addClass( 'pp-mobile-icon-landscape' );
					}
					else if ( $(this).hasClass( 'pp-mobile-icon-landscape' ) ){
						self.elements.$deviceContainer.removeClass( 'pp-device-orientation-landscape' );
						self.elements.$deviceContainer.addClass( 'pp-device-orientation-portrait' );
						$(this).addClass( 'pp-mobile-icon-portrait' );
						$(this).removeClass( 'pp-mobile-icon-landscape' );
					}
				});
			}

			async initSlider() {
				const elementSettings = this.getElementSettings();

				const Swiper = elementorFrontend.utils.swiper;
    			this.swiper = await new Swiper(this.elements.$swiperContainer, this.getSwiperOptions());

				if ('yes' === elementSettings.pause_on_hover) {
					this.togglePauseOnHover(true);
				}

				// this.setEqualHeight();
			}

			togglePauseOnHover(toggleOn) {
				if (toggleOn) {
					this.elements.$swiperContainer.on({
						mouseenter: () => {
							this.swiper.autoplay.stop();
						},
						mouseleave: () => {
							this.swiper.autoplay.start();
						}
					});
				} else {
					this.elements.$swiperContainer.off('mouseenter mouseleave');
				}
			}

			setEqualHeight() {
				let height = 0;

				this.elements.$swiperSlide.each(function () {
					if ( $(this).height() > height) {
						height = $(this).height();
					}
				});

				this.elements.$swiperContainer.css( 'height', (height + 70) + 'px' );
			}
		}

		elementorFrontend.elementsHandler.attachHandler( 'pp-devices', DevicesWidget );
	} );
})(jQuery);