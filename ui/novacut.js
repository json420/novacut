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

    this.playing = false;
    this.ready = false;
    this.ended = false;

    this.onready = null;
    this.onended = null;
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
        //this.log_event('seeked', this.slice.node.start.frame);
        if (!this.ready) {
            this.ready = true;
            if (this.onready) {
                this.onready(this);
            }
        }
    },

    on_ended: function(event) {
        this.video.pause();
        this.clear_timeout();
        //this.log_event('ended', this.slice.node.stop.frame);
        this.ended = true;
        if (this.onended) {
            this.onended(this);
        }
    },

    seek: function(frame) {
        this.video.currentTime = this.frame_to_seconds(frame);
    },

    frame_to_seconds: function(frame) {
        return frame_to_seconds(frame, this.clip.framerate);
    },

    clear_timeout: function() {
        if (this.timeout_id != null) {
            clearTimeout(this.timeout_id);
            this.timeout_id = null;
        }
    },

    set_timeout: function(duration) {
        this.clear_timeout();
        var callback = $bind(this.on_ended, this);
        this.timeout_id = setTimeout(callback, duration);
    },

    playpause: function() {
        if (this.playing) {
            this.pause();
        }
        else {
            this.play();
        }
    },

    play: function() {
        if (this.playing || !this.ready) {
            return;
        }
        this.playing = true;
        this.video.style.visibility = 'visible';
        if (this.slice.node.stop.frame != this.clip.duration.frames) {     
            var stop = this.frame_to_seconds(this.slice.node.stop.frame);
            var duration = 1000 * (stop - this.video.currentTime);
            this.set_timeout(duration);
        }
        this.video.play();
    },

    pause: function() {
        if (!this.ready) {
            return;
        }
        this.playing = false;
        this.video.style.visibility = 'visible';
        this.clear_timeout();
        this.video.pause();
    },
    
    stop: function() {
        this.video.style.visibility = 'hidden';
        this.video.pause();
        this.clear_timeout();
        this.ended = false;
        this.ready = false;
        this.playing = false;
    },

    load_slice: function(clip, slice) {
        this.stop();
        this.clip = clip;
        this.slice = slice;
        this.video.src = 'dmedia:' + this.clip._id;
        //setTimeout($bind(this.do_load, this), 50);
    },

    do_load: function() {
        this.video.src = 'dmedia:' + this.clip._id;
    },
}



function SequencePlayer(session, doc) {
    this.session = session;
    this.doc = doc;

    this.element = $el('div', {'id': 'player', 'class': 'hide'});

    this.player1 = new SlicePlayer();
    this.player1.i = 0;
    this.player2 = new SlicePlayer();
    this.player2.i = 1;

    this.players = [this.player1, this.player2];
    var on_ready = $bind(this.on_ready, this);
    var on_ended = $bind(this.on_ended, this);
    this.players.forEach(function(player) {
        player.onready = on_ready;
        player.onended = on_ended;
        this.element.appendChild(player.video);
    }, this);

    this.ready = false;
    this.playing = false;
    this.active = false;
    
    this.element.onclick = $bind(this.playpause, this);

    document.body.appendChild(this.element);

}
SequencePlayer.prototype = {
    show: function() {
        console.log('show');
        if (this.doc.node.src.length == 0) {
            return;
        }
        $show(this.element);
        this.active = true;
        this.playing = true;
        this.play_from_slice(UI.selected);
    },

    hide: function() {
        console.log('hide');
        $hide(this.element);
        this.active = false;
        this.stop();
    },

    playpause: function() {
        if (this.playing) {
            this.pause();  
        }
        else {
            this.play();
        }
    },

    hold: function() {
        this.was_playing = this.playing;
        this.playing = false;
        this.activate_target(true);
    },

    resume: function(slice_id) {
        this.playing = this.was_playing;
        if (slice_id) {
            this.play_from_slice(slice_id);
        }
        else {
            this.activate_target();
        }
    },

    stop: function() {
        this.players.forEach(function(player) {
            player.stop();
        });
        this.ready = false;
        this.target = null;
    },

    play: function() {
        this.playing = true;
        this.activate_target();
    },

    pause: function() {
        this.playing = false;
        this.activate_target();
    },

    play_from_slice: function(slice_id) {
        if (this.doc.node.src.length == 0) {
            return;
        }
        this.stop();
        if (!slice_id) {
            slice_id = UI.selected;
        }
        console.log('play_from_slice ' + slice_id);
        var index = Math.max(0, this.doc.node.src.indexOf(slice_id));
        this.load_slice(this.player1, index);
        this.load_slice(this.player2, index + 1);
    },

    get_player: function(i) {
        return this.players[i % this.players.length];
    },

    next_slice_index: function(player) {
        return this.doc.node.src.indexOf(player.slice._id) + 1;
    },

    load_slice: function(player, index) {
        var src = this.doc.node.src;
        var slice_id = src[index % src.length];
        var slice = this.session.get_doc(slice_id);
        var clip = this.session.get_doc(slice.node.src);
        player.load_slice(clip, slice);
    },

    on_ready: function(player) {
        if (!this.ready) {
            if (this.player1.ready && this.player2.ready) {
                console.log('now ready');
                this.ready = true;
                this.target = this.players[0];
                this.activate_target();
            }
        }
        else if (this.target.ended) {
            this.swap();
        }
    },

    activate_target: function(no_select) {
        if (!this.target) {
            return;
        }
        if (this.playing) {
            this.target.play();
        }
        else {
            this.target.pause();
        }
        if (!no_select) {
            UI.select(this.target.slice._id, true);
        }
    },

    swap: function() {
        var current = this.target;
        var next = this.get_player(current.i + 1);
        if (next.ready) {
            this.target = next;
            var index = this.next_slice_index(next);
            this.activate_target();
            this.load_slice(current, index);
        } 
    },

    on_ended: function(player) {
        this.swap();
    },
}



