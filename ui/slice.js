"use strict";


function $halt(event) {
    event.preventDefault();
    event.stopPropagation();
}


function frame_to_seconds(frame, framerate) {
    return frame * framerate.denom / framerate.num;
}


function seconds_to_frame(seconds, framerate) {
    return Math.round(seconds * framerate.num / framerate.denom);
}


var VideoFrame = function(id) {
    this.video = $(id);
    this.pending = null;
    this.current = null;
}
VideoFrame.prototype = {
    seek: function(seconds) {
        this.pending = seconds;
    },

    do_seek: function() {
        if (this.pending != this.current) {
            this.current = this.pending;
            this.video.currentTime = this.pending;
        }
    },

    set_src: function(uri) {
        this.pending = 0;
        this.current = 0;
        this.video.src = uri;
        this.video.load();
    },
}


var UI = {
    init: function() {
        console.log('init');
        var parts = parse_hash();
        UI.project_id = parts[0];
        UI.slice_id = parts[1];
        var doc = novacut.get_sync(UI.project_id);
        UI.db = new couch.Database(doc.db_name);

        UI.slice = UI.db.get_sync(UI.slice_id);
        UI.clip = UI.db.get_sync(UI.slice.node.src);

        UI.scrubber = $('scrubber');
        UI.scrubber.addEventListener('mousedown', UI.on_mousedown);
        UI.scrubber.addEventListener('mousemove', UI.on_scrub_start);

        UI.startframe = new VideoFrame('startframe');
        UI.endframe = new VideoFrame('endframe');
        
        UI.bar = $('bar');
        
        var uri = 'dmedia:' + UI.clip._id;
        UI.startframe.set_src(uri);
        $hide(UI.endframe);
        UI.endframe.set_src(uri);

        UI.intervalID = setInterval(UI.on_interval, 100);
    },

    on_interval: function() {
        UI.startframe.do_seek();
        UI.endframe.do_seek();
    },

    get_frame: function(event) {
        var width = UI.scrubber.clientWidth - 4;
        var x = Math.max(0, Math.min(event.pageX - 2, width));
        var percent = x / width;
        var precise = Math.round(percent * (UI.clip.duration.frames - 1));
        var rough = Math.round(precise / 15) * 15;
        return rough + 1;
    },

    set_start: function(frame) {
        UI.start = frame;
        UI.startframe.seek(frame_to_seconds(frame, UI.clip.framerate));
    },

    set_end: function(frame) {
        UI.stop = frame + 1;
        UI.endframe.seek(frame_to_seconds(frame, UI.clip.framerate));
    },

    on_mousedown: function(event) {
        console.log('mousedown');
        $halt(event);
        UI.scrubber.removeEventListener('mousemove', UI.on_scrub_start);
        window.addEventListener('mousemove', UI.on_scrub_end);
        window.addEventListener('mouseup', UI.on_mouseup);
        UI.start_pos = event.pageX;
        $show(UI.bar);
        $show(UI.endframe.video);
        UI.set_end(UI.get_frame(event));
    },

    on_mouseup: function(event) {
        console.log('mouseup');
        $halt(event);
        window.removeEventListener('mousemove', UI.on_scrub_end);
        window.removeEventListener('mouseup', UI.on_mouseup);
    },

    on_scrub_start: function(event) {
        $halt(event);
        UI.set_start(UI.get_frame(event));
    },

    on_scrub_end: function(event) {
        $halt(event);
        var width = event.pageX - UI.start_pos;
        if (width < 0) {
        	UI.bar.style.left = (UI.start_pos + width) + 'px';
        }
        else {
        	UI.bar.style.left = UI.start_pos + 'px';
        }
        UI.bar.style.width = Math.abs(width) + 'px';
        UI.set_end(UI.get_frame(event));
    },
}

window.addEventListener('load', UI.init);
