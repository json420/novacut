"use strict";

var novacut = new couch.Database('novacut-0');
var dmedia = new couch.Database('dmedia-0');

function parse_hash() {
    return window.location.hash.slice(1).split('/');
}

function set_title(id, value) {
    var el = $(id);
    if (value) {
        el.textContent = value;
    }
    else {
        el.textContent = '';
        el.appendChild($el('em', {textContent: 'Untitled'}));
    }
    return el;
}


function project_db(base, ver, project_id) {
    var name = [base, ver, project_id.toLowerCase()].join('-');
    return new couch.Database(name);
}


function novacut_project_db(project_id) {
    return project_db('novacut', 0, project_id);
}


function dmedia_project_db(project_id) {
    return project_db('dmedia', 0, project_id);
}


function frame_to_seconds(frame, framerate) {
    return frame * framerate.denom / framerate.num;
}


function seconds_to_frame(seconds, framerate) {
    return Math.round(seconds * framerate.num / framerate.denom);
}



function create_node(node) {
    return {
        '_id': couch.random_id(),
        'ver': 0,
        'type': 'novacut/node',
        'time': couch.time(),
        'node': node,
    }
}


function create_slice(src, frame_count) {
    var node = {
        'type': 'slice',
        'src': src,
        'start': {'frame': 0},
        'stop': {'frame': frame_count},
        'stream': 'video',
    }
    return create_node(node);
}


function create_sequence() {
    var node = {
        'type': 'sequence',
        'src': [],
    }
    var doc = create_node(node);
    doc.doodle = [];
    return doc;
}


function SlicePlayer() {
    this.video = document.createElement('video');
    this.video.muted = true;
    this.video.addEventListener('canplaythrough',
        $bind(this.on_canplaythrough, this)
    );
    this.video.addEventListener('seeked',
        $bind(this.on_seeked, this)
    );
    this.video.addEventListener('ended',
        $bind(this.on_ended, this)
    );
    this.timeout_id = null;
    this.state = 'stop';
    this.ready = false;
    this.seeking = false;
    this.repeat = false;
    this.video.onclick = $bind(this.playpause, this);

    this.onready = null;
    
}

SlicePlayer.prototype = {
    log_event: function(name, point) {
        var frame = seconds_to_frame(this.video.currentTime, this.clip.framerate);
        var parts = [name, frame, point, frame == point];
        console.log(parts.join(' '));
    },

    on_canplaythrough: function(event) {
        this.seek(this.slice.node.start.frame);
    },

    on_seeked: function(event) {
        this.seeking = false;
        this.log_event('seeked', this.slice.node.start.frame);
        if (!this.ready) {
            this.ready = true;
            if (this.onready) {
                this.onready(this);
            }
        }
        this._restore();
    },

    on_ended: function(event) {
        this._pause();
        this.log_event('ended', this.slice.node.stop.frame);
        if (this.repeat) {
            this.seek(this.slice.node.start.frame);
        }
    },

    seek: function(frame) {
        this.seeking = true;
        this._pause();
        this.video.currentTime = this.frame_to_seconds(frame);
    },

    frame_to_seconds: function(frame) {
        return frame_to_seconds(frame, this.clip.framerate);
    },

    playpause: function() {
        if (this.state == 'playing') {
            this.pause();
        }
        else {
            this.play();
        }
    },

    play: function() {
        this.set_state('playing');
    },

    pause: function() {
        this.set_state('paused');
    },

    stop: function() {
        this.state = 'stopped';
        this._stop();
    },

    set_state: function(state) {
        console.log('set_state ' + state);
        this.state = state;
        if (this.seeking || !this.ready) {
            return;
        }
        if (this.state == 'paused') {
            this._pause();
        }
        else {
            this._play();
        }
    },

    _restore: function() {
        if (this.state == 'stop') {
            return;
        }
        this.video.style.visibility = 'visible';
        if (this.state == 'playing') {
            this._play();
        }
    },

    clear_timeout: function() {
        if (this.timeout_id != null) {
            clearTimeout(this.timeout_id);
            this.timeout_id = null;
        }
    },

    set_timeout: function(duration) {
        console.assert(this.timeout_id == null);
        var callback = $bind(this.on_ended, this);
        this.timeout_id = setTimeout(callback, duration);
    },

    _play: function(frame) {
        if (this.slice.node.stop.frame != this.clip.duration.frames) {     
            var stop = this.frame_to_seconds(this.slice.node.stop.frame);
            var duration = 1000 * (stop - this.video.currentTime);
            this.set_timeout(duration);
        }
        this.video.play();
    },

    _pause: function(frame) {
        this.clear_timeout();
        this.video.pause();
    },

    _stop: function() {
        this.clear_timeout();
        this.video.pause();
        this.video.style.visibility = 'hidden';
        this.ready = false;
        this.seeking = false;
    },

    load_slice: function(clip, slice) {
        this._stop();
        this.clip = clip;
        this.slice = slice;
        this.video.src = 'dmedia:' + clip._id;
    },

    play_slice: function(clip, slice) {
        this.load_slice(clip, slice);
    },
}



function SequencePlayer() {

}
SequencePlayer.prototype = {
    
}



