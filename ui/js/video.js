/*
JS Video Library for Novacut
Author: JamesMR - james@haiku.im
Depends on jQuery
*/

function Video(id){
	this.id = id;
	this.framerate = 25;
	this.playing = false;
	this.playingreverse = false;
	
	//How many frames are in the clip?
	this.frames = function(){
		return (Math.floor($('#'+this.id)[0].duration*this.framerate));
	}
	
	//play the video
	this.play = function(){
		if (this.playing)this.pause();
		$('#'+this.id)[0].play();
		this.playing = true;
	}
	
	this.playReverse = function(){
		this.pause();
		this.playingreverse = true;
		this.playing = true;
		//RAGE THIS DOESN'T WORK!
	}
	
	//pause the video
	this.pause = function(){
		$('#'+this.id)[0].pause();
		this.playing = false;
		this.playingreverse = false
	}
	
	//like a play/pause button
	this.toggleplay = function(){
		if (this.playing || this.playingreverse)this.pause();
		else this.play();
	}
	
	this.togglereverse = function(){
		if (this.playing || this.playingreverse)this.pause();
		else this.playReverse();
	}
	
	//stop the video
	this.stop = function(){
		this.pause();
		this.setFrame(0);
	}
	
	//return the current frame number
	this.getFrame = function(){
		return (Math.round($('#'+this.id)[0].currentTime*this.framerate));
	}
	
	//go to a specific frame
	this.setFrame = function(frame){
		$('#'+this.id)[0].currentTime = frame/this.framerate;
	}
	
	//step forward or back the specified number of frames
	this.step = function(frames){
		$('#'+this.id)[0].currentTime += frames/this.framerate;
	}
	
	//return the playback position - float between 0 and 1
	this.getPosition = function(){
		element = $('#'+this.id)[0];
		inverse = (element.duration - element.currentTime)/element.duration;
		position = (inverse - 0.5)*-1 + 0.5;
		return (position);
	}
}
