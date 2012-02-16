"use strict";

var id = window.location.hash.slice(1);

var doc = novacut.get_sync(id);
var db = new couch.Database(doc.db_name);
var doc = db.get_sync(id);


function css_url(url) {
    return ['url(', JSON.stringify(url), ')'].join('');
}

//thumb.style.backgroundImage

var Thumbs = {
    db: new couch.Database('thumbnails'), 

    docs: {},

    do_load: function(file_id, start, end) {
        Hub.send('thumbnail', file_id, [start, end]);
    },

    set_thumbnail: function(slice, file_id, start, stop) {
        var end = stop - 1;
        if (!Thumbs.docs[file_id]) {
            console.log('loading doc');
            try {
                Thumbs.docs[file_id] = Thumbs.db.get_sync(file_id);
            }
            catch (e) {
                return Thumbs.do_load(file_id, start, end);
            }
        }
        var doc = Thumbs.docs[file_id];
        if (doc._attachments[start] && doc._attachments[end]) {
            return;
        }
        Thumbs.do_load(file_id, start, end);
        //div.style.backgroundImage = Thumbs.db.att_css_url(file_id, frame_index);
    },

    on_thumbnail_finished: function(file_id) {
        console.log(['finished', file_id].join(' '));
    },

    has_frame: function(file_id, index) {
        if (!Thumbs.docs[file_id]) {
            try {
                Thumbs.docs[file_id] = Thumbs.db.get_sync(file_id);
            }
            catch (e) {
                return false;
            }
        }
        if (Thumbs.docs[file_id]._attachments[index]) {
            return true;
        }
        return false;
    },

    q: {},

    enqueue: function(frame) {
        if (!Thumbs.q[frame.file_id]) {
            Thumbs.q[frame.file_id] = [];
        }
        Thumbs.q[frame.file_id].push(frame);
    },

    flush: function() {
        var ids = Object.keys(Thumbs.q);
        if (ids.length == 0) {
            return;
        }
        ids.forEach(function(id) {
            var frames = Thumbs.q[id];
            var needed = [];
            frames.forEach(function(frame) {
                if (Thumbs.has_frame(id, frame.index)) {
                    frame.request_thumbnail.call(frame);
                }
                else {
                    needed.push(frame.index);
                }
            });
            console.log(needed.join(', '));
        }); 
    },
}

Hub.connect('thumbnail_finished', Thumbs.on_thumbnail_finished);


var Frame = function(file_id, index) {
    this.file_id = file_id;
    this.element = $el('div');
    this.set_index(index);
}
Frame.prototype = {
    set_index: function(index) {
        this.index = index;
        this.element.style.backgroundImage = null;
        this.element.textContent = index + 1;
        Thumbs.enqueue(this);
    },

    request_thumbnail: function() {
        this.element.style.backgroundImage = Thumbs.db.att_css_url(this.file_id, this.index);
    },

}


var UI = {
    init: function() {
        set_title('title', doc.title);
        var seq = db.get_sync(doc.root_id);
        console.log(seq);
        db.post(UI.on_rows, {keys: seq.node.src}, '_all_docs', {include_docs: true});

    },

    on_rows: function(req) {
        var rows = req.read().rows;
        var sequence = $('sequence');
        rows.forEach(function(row) {
            var slice = $el('div', {'class': 'slice', 'id': row.id});
            var node = row.doc.node;

            var start = new Frame(node.src, node.start.frame);
            slice.appendChild(start.element);

            var end = new Frame(node.src, node.stop.frame - 1);
            slice.appendChild(end.element);

            sequence.appendChild(slice);
        });
        Thumbs.flush();
    },
}

window.addEventListener('load', UI.init);

Hub.connect('render_finished',
    function(job_id, file_id) {
        var player = $('player');
        player.src = 'dmedia:' + file_id;
        player.play();
    }
);
