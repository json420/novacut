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
    
    do_load: function(file_id, frame_index) {
        var chunk = Math.floor(frame_index / 15);
        Hub.send('thumbnail', file_id, chunk);
    },

    set_thumbnail: function(div, file_id, frame_index) {
        if (!Thumbs.docs[file_id]) {
            console.log('loading doc');
            try {
                Thumbs.docs[file_id] = Thumbs.db.get_sync(file_id);
            }
            catch (e) {
                return Thumbs.do_load(file_id, frame_index);
            }
        }
        if (!Thumbs.docs[file_id]._attachments[frame_index]) {
            return Thumbs.do_load(file_id, frame_index);
        }
        div.style.backgroundImage = Thumbs.db.att_css_url(file_id, frame_index);
    },

    on_thumbnail_finished: function(file_id, chunk) {
        console.log(['finished', file_id, chunk].join(' '));
    },
}

Hub.connect('thumbnail_finished', Thumbs.on_thumbnail_finished);


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

            var start = $el('div', {textContent: (node.start.frame + 1)});
            Thumbs.set_thumbnail(start, node.src, node.start.frame);
            slice.appendChild(start);

            var stop = $el('div', {textContent: node.stop.frame});
            Thumbs.set_thumbnail(stop, node.src, (node.stop.frame - 1));
            slice.appendChild(stop);

            sequence.appendChild(slice);
        });
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
