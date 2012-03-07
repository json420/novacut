"use strict";


function $halt(event) {
    event.preventDefault();
    event.stopPropagation();
}


function frame_to_seconds(frame, framerate) {
    return frame * framerate.denom / framerate.num;
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

        UI.startframe = $('startframe');
        UI.endframe = $('endframe');
        
        var uri = 'dmedia:' + UI.clip._id;
        UI.startframe.src = uri;
        UI.startframe.load();
        $hide(UI.endframe);
        UI.endframe.src = uri;
        UI.endframe.load();
    },

    get_frame: function(event) {
        var width = UI.scrubber.clientWidth - 4;
        var x = Math.max(0, Math.min(event.pageX - 2, width));
        var percent = x / width;
        return Math.round(percent * (UI.clip.duration.frames - 1));
    },

    set_start: function(frame) {
        UI.start = frame;
        UI.startframe.currentTime = frame_to_seconds(frame, UI.clip.framerate);
    },

    set_end: function(frame) {
        UI.stop = frame + 1;
        UI.endframe.currentTime = frame_to_seconds(frame, UI.clip.framerate);
    },

    on_mousedown: function(event) {
        console.log('mousedown');
        $halt(event);
        UI.scrubber.removeEventListener('mousemove', UI.on_scrub_start);
        window.addEventListener('mousemove', UI.on_scrub_end);
        window.addEventListener('mouseup', UI.on_mouseup);
        $show(UI.endframe);
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
        UI.set_end(UI.get_frame(event));
    },
}

window.addEventListener('load', UI.init);
